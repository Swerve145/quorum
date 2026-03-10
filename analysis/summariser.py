# meeting summarisation using T5 with extractive pre-filter
import re
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Summariser:
    """Produces structured meeting summaries from aligned transcript"""

    def __init__(self, config=None):
        self.config = config or {}
        self.model_name = self.config.get("summary_model", "t5-base")
        self.model = None        
        self.tokenizer = None
        self.device = None

        # T5-small max input is 512 tokens — we aim for ~400
        # to leave headroom for the prompt prefix
        self.max_input_tokens = self.config.get("max_input_tokens", 400)

        # Patterns that indicate high-signal sentences
        self.decision_patterns = [
            re.compile(r"\b(decided|agreed|confirmed|approved|going with)\b", re.IGNORECASE),
            re.compile(r"\b(let\'?s go with|we\'ll|final decision)\b", re.IGNORECASE),
        ]
        self.topic_patterns = [
            re.compile(r"\b(moving on to|next (point|topic|item)|regarding|about the)\b", re.IGNORECASE),
            re.compile(r"\b(let\'?s (talk|discuss)|agenda item)\b", re.IGNORECASE),
        ]
        self.disagreement_patterns = [
            re.compile(r"\b(disagree|not sure about|concerned|but I think|on the other hand)\b", re.IGNORECASE),
            re.compile(r"\b(issue with|problem with|don\'?t agree)\b", re.IGNORECASE),
        ]

        logger.info("Summariser initialised")

    def load_model(self):
        import torch
        from transformers import T5Tokenizer, T5ForConditionalGeneration

        logger.info("Loading T5-small for summarisation...")

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        logger.info(f"{self.model_name} loaded. Device: {self.device}")

    def _extract_key_sentences(self, segments):
        # Layer 1: Extractive pre-filter.
        scored = []

        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            score = 0
            signal_types = []

            # Check decision patterns
            for pattern in self.decision_patterns:
                if pattern.search(text):
                    score += 3  # Decisions are highest priority
                    signal_types.append("decision")
                    break

            # Check topic patterns
            for pattern in self.topic_patterns:
                if pattern.search(text):
                    score += 2
                    signal_types.append("topic")
                    break

            # Check disagreement patterns
            for pattern in self.disagreement_patterns:
                if pattern.search(text):
                    score += 2
                    signal_types.append("disagreement")
                    break

            # Longer sentences tend to carry more content
            word_count = len(text.split())
            if word_count > 10:
                score += 1

            scored.append({
                "text": text,
                "speaker": seg.get("speaker", "UNKNOWN"),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "score": score,
                "signal_types": signal_types,
            })

        # Sort by score descending, then by timestamp for tie-breaking
        scored.sort(key=lambda x: (-x["score"], x["start"]))

        # Select sentences until we approach the token limit
        selected = []
        token_count = 0

        for item in scored:
            # Rough token estimate: words * 1.3
            estimated_tokens = int(len(item["text"].split()) * 1.3)

            if token_count + estimated_tokens > self.max_input_tokens:
                break

            selected.append(item)
            token_count += estimated_tokens

        # Re-sort selected by timestamp so the summary input
        # follows chronological order
        selected.sort(key=lambda x: x["start"])

        logger.info(
            f"Extractive filter: {len(selected)}/{len(scored)} "
            f"sentences selected (~{token_count} tokens)"
        )

        return selected

    def _build_prompt(self, key_sentences):
        lines = []
        for sent in key_sentences:
            lines.append(f"{sent['speaker']}: {sent['text']}")

        transcript_text = " ".join(lines)

        prompt = f"summarize: {transcript_text}"

        return prompt

    def _generate_summary(self, prompt):
        # Layer 2: Run T5-small on the prepared prompt.
        import torch

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=150,
                min_length=30,
                num_beams=4,          # Beam search for better quality
                length_penalty=1.2,   # Slightly favour longer outputs
                no_repeat_ngram_size=3,  # Prevent repetition
                early_stopping=True,
            )

        summary_text = self.tokenizer.decode(
            outputs[0], skip_special_tokens=True
        )

        logger.info(f"T5 generated summary: {len(summary_text)} chars")

        return summary_text

    def _extract_decisions(self, segments):
        decisions = []

        for seg in segments:
            text = seg.get("text", "").strip()
            for pattern in self.decision_patterns:
                if pattern.search(text):
                    decisions.append({
                        "text": text,
                        "speaker": seg.get("speaker", "UNKNOWN"),
                        "timestamp": seg.get("start", 0),
                    })

        logger.info(f"Extracted {len(decisions)} decisions")
        return decisions

    def _extract_topics(self, key_sentences):
        topics = []
        current_topic_sentences = []

        for sent in key_sentences:
            # Topic shift detected
            if "topic" in sent.get("signal_types", []):
                # Save previous topic if exists
                if current_topic_sentences:
                    topics.append({
                        "sentences": current_topic_sentences,
                        "start": current_topic_sentences[0]["start"],
                        "end": current_topic_sentences[-1]["end"],
                    })
                current_topic_sentences = [sent]
            else:
                current_topic_sentences.append(sent)

        # Don't forget the last group
        if current_topic_sentences:
            topics.append({
                "sentences": current_topic_sentences,
                "start": current_topic_sentences[0]["start"],
                "end": current_topic_sentences[-1]["end"],
            })

        logger.info(f"Identified {len(topics)} topic groups")
        return topics

    def summarise(self, aligned_segments):
        # Full summarisation pipeline.
        if not aligned_segments:
            logger.warning("No segments provided to summariser")
            return {
                "overview": "",
                "decisions": [],
                "topics": [],
                "key_sentences": [],
                "metadata": {"segment_count": 0},
            }

        # Ensure model is loaded
        if self.model is None:
            self.load_model()

        logger.info(
            f"Summarising {len(aligned_segments)} segments"
        )

        key_sentences = self._extract_key_sentences(aligned_segments)

        prompt = self._build_prompt(key_sentences)
        overview = self._generate_summary(prompt)

        decisions = self._extract_decisions(aligned_segments)
        topics = self._extract_topics(key_sentences)

        result = {
            "overview": overview,
            "decisions": decisions,
            "topics": topics,
            "key_sentences": key_sentences,
            "metadata": {
                "segment_count": len(aligned_segments),
                "key_sentences_count": len(key_sentences),
                "decision_count": len(decisions),
                "topic_count": len(topics),
            },
        }

        logger.info(
            f"Summarisation complete: {len(decisions)} decisions, "
            f"{len(topics)} topics, overview {len(overview)} chars"
        )

        return result
