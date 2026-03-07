# task extraction — v1 (rule-based) and v2 (DistilBERT)
import re
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Action patterns: phrases that signal someone committing to do something
ACTION_PATTERNS = [
    r"\b(i'll|i will|i am going to|i'm going to)\b",
    r"\b(we need to|we should|we have to|we must)\b",
    r"\b(can you|could you|would you|please)\b",
    r"\b(action item|todo|to-do|task)\b",
    r"\b(make sure|ensure|don't forget|remember to)\b",
    r"\b(let's|let us)\b",
    r"\b(you need to|you should|you have to)\b",
    r"\b(assigned to|responsible for|owner)\b",
    r"\b(follow up|circle back|get back to)\b",
    r"\b(deadline|due date|by end of)\b",
]

# Deadline patterns: phrases that indicate a timeframe
DEADLINE_PATTERNS = [
    (r"\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "day"),
    (r"\bby end of (week|day|month)\b", "relative"),
    (r"\bby (\d{1,2}(?:st|nd|rd|th)?(?:\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)?)\b", "date"),
    (r"\bwithin (\d+)\s+(hours?|days?|weeks?)\b", "duration"),
    (r"\b(today|tomorrow|tonight|asap|immediately|urgently)\b", "urgency"),
]

# Priority signals
HIGH_PRIORITY_SIGNALS = [
    r"\b(urgent|urgently|critical|asap|immediately|top priority)\b",
    r"\b(must|crucial|essential|blocking|blocker)\b",
]

LOW_PRIORITY_SIGNALS = [
    r"\b(when you get a chance|no rush|low priority|eventually)\b",
    r"\b(nice to have|if possible|at some point)\b",
]


class TaskExtractor:
    """Extracts tasks from aligned transcript segments."""

    def __init__(self, config=None):
        self.config = config or {}
        self.min_confidence = self.config.get("min_task_confidence", 0.3)

        # Compile patterns once at init for performance
        self.action_patterns = [
            re.compile(p, re.IGNORECASE) for p in ACTION_PATTERNS
        ]
        self.deadline_patterns = [
            (re.compile(p, re.IGNORECASE), label)
            for p, label in DEADLINE_PATTERNS
        ]
        self.high_priority = [
            re.compile(p, re.IGNORECASE) for p in HIGH_PRIORITY_SIGNALS
        ]
        self.low_priority = [
            re.compile(p, re.IGNORECASE) for p in LOW_PRIORITY_SIGNALS
        ]

        logger.info("TaskExtractor initialised (rule-based v1)")

    def extract(self, aligned_segments: list) -> list:
        """Process aligned transcript segments and extract tasks."""
        logger.info(
            f"Extracting tasks from {len(aligned_segments)} segments"
        )

        tasks = []

        for segment in aligned_segments:
            text = segment.get("text", "")
            if not text.strip():
                continue

            # Split into sentences for finer-grained detection
            sentences = self._split_sentences(text)

            for sentence in sentences:
                task = self._evaluate_sentence(sentence, segment)
                if task is not None:
                    tasks.append(task)

        logger.info(f"Extracted {len(tasks)} tasks (v1 rule-based)")
        return tasks

    def _split_sentences(self, text: str) -> list:
        # Protect common abbreviations
        protected = text.replace("Mr.", "Mr").replace("Mrs.", "Mrs")
        protected = protected.replace("Dr.", "Dr").replace("etc.", "etc")
        protected = protected.replace("e.g.", "eg").replace("i.e.", "ie")

        # Split on sentence-ending punctuation
        parts = re.split(r'(?<=[.!?])\s+', protected)

        # Restore abbreviations and filter empties
        sentences = [s.strip() for s in parts if s.strip()]
        return sentences

    def _evaluate_sentence(self, sentence: str, segment: dict) -> dict:
        # Score a single sentence against task patterns.
        # Count action pattern matches
        action_matches = 0
        matched_patterns = []

        for pattern in self.action_patterns:
            if pattern.search(sentence):
                action_matches += 1
                matched_patterns.append(pattern.pattern)

        # No action patterns matched — not a task
        if action_matches == 0:
            return None

        # Calculate confidence: proportion of pattern categories hit
        confidence = min(action_matches / 3.0, 1.0)

        # Extract deadline if present
        deadline = self._extract_deadline(sentence)
        if deadline is not None:
            confidence = min(confidence + 0.2, 1.0)

        # Determine priority
        priority = self._assess_priority(sentence)

        # Determine assignee from context
        assignee = self._determine_assignee(sentence, segment)

        # Apply threshold
        if confidence < self.min_confidence:
            return None

        task = {
            "task_text": sentence.strip(),
            "assignee": assignee,
            "deadline": deadline,
            "priority": priority,
            "confidence": round(confidence, 3),
            "source_segment": {
                "speaker": segment.get("speaker", "UNKNOWN"),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
            },
            "matched_patterns": matched_patterns,
        }

        logger.debug(
            f"Task detected (conf={confidence:.2f}): "
            f"{sentence[:60]}..."
        )

        return task

    def _extract_deadline(self, sentence: str) -> str:
        for pattern, deadline_type in self.deadline_patterns:
            match = pattern.search(sentence)
            if match:
                return match.group(0)
        return None

    def _assess_priority(self, sentence: str) -> str:
        for pattern in self.high_priority:
            if pattern.search(sentence):
                return "high"

        for pattern in self.low_priority:
            if pattern.search(sentence):
                return "low"

        return "medium"

    def _determine_assignee(self, sentence: str, segment: dict) -> str:
        speaker = segment.get("speaker", "UNKNOWN")

        # Self-assignment patterns
        self_patterns = [
            r"\b(i'll|i will|i am going to|i'm going to|let me)\b"
        ]
        for p in self_patterns:
            if re.search(p, sentence, re.IGNORECASE):
                return speaker

        # Delegation patterns — flag for later resolution
        delegation_patterns = [
            r"\b(can you|could you|would you|you need to|you should)\b"
        ]
        for p in delegation_patterns:
            if re.search(p, sentence, re.IGNORECASE):
                return f"{speaker}→DELEGATE"

        return speaker

class TaskExtractorV2:
    """v2: Fine-tuned DistilBERT task classifier."""

    def __init__(self, checkpoint_dir: str, config=None):
        self.config = config or {}
        self.checkpoint_dir = checkpoint_dir
        self.min_confidence = self.config.get("min_task_confidence", 0.5)

        self.tokenizer = None
        self.model = None
        self.device = None

        logger.info("TaskExtractorV2 initialised (DistilBERT)")

    def load_model(self):
        import torch
        from transformers import (
            DistilBertTokenizer,
            DistilBertForSequenceClassification
        )

        logger.info(f"Loading fine-tuned model from: {self.checkpoint_dir}")

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.tokenizer = DistilBertTokenizer.from_pretrained(
            self.checkpoint_dir
        )
        self.model = DistilBertForSequenceClassification.from_pretrained(
            self.checkpoint_dir
        )
        self.model.to(self.device)
        self.model.eval()

        logger.info(f"Model loaded. Device: {self.device}")

    def extract(self, aligned_segments: list) -> list:
        # Process aligned transcript segments using the
        import torch

        if self.model is None:
            self.load_model()

        logger.info(
            f"Extracting tasks from {len(aligned_segments)} segments (v2)"
        )

        tasks = []

        for segment in aligned_segments:
            text = segment.get("text", "")
            if not text.strip():
                continue

            sentences = self._split_sentences(text)

            for sentence in sentences:
                task = self._classify_sentence(sentence, segment)
                if task is not None:
                    tasks.append(task)

        logger.info(f"Extracted {len(tasks)} tasks (v2 DistilBERT)")
        return tasks

    def _split_sentences(self, text: str) -> list:
        protected = text.replace("Mr.", "Mr").replace("Mrs.", "Mrs")
        protected = protected.replace("Dr.", "Dr").replace("etc.", "etc")
        protected = protected.replace("e.g.", "eg").replace("i.e.", "ie")

        parts = re.split(r'(?<=[.!?])\s+', protected)
        sentences = [s.strip() for s in parts if s.strip()]
        return sentences

    def _classify_sentence(self, sentence: str, segment: dict) -> dict:
        """Run a single sentence through the fine-tuned model."""
        import torch

        # Tokenise
        encoding = self.tokenizer(
            sentence,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        # Inference
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

        # Convert logits to probabilities
        probabilities = torch.softmax(outputs.logits, dim=1)
        task_prob = probabilities[0][1].item()  # probability of class 1
        predicted_class = torch.argmax(probabilities, dim=1).item()

        # Not a task
        if predicted_class == 0 or task_prob < self.min_confidence:
            return None

        # Determine assignee using same logic as v1
        assignee = self._determine_assignee(sentence, segment)

        # Deadline extraction reuses v1 patterns — still useful
        deadline = self._extract_deadline(sentence)

        # Priority from v1 patterns — model doesn't predict this
        priority = self._assess_priority(sentence)

        task = {
            "task_text": sentence.strip(),
            "assignee": assignee,
            "deadline": deadline,
            "priority": priority,
            "confidence": round(task_prob, 3),
            "source_segment": {
                "speaker": segment.get("speaker", "UNKNOWN"),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
            },
            "extraction_method": "distilbert_v2",
        }

        logger.debug(
            f"Task detected (prob={task_prob:.3f}): "
            f"{sentence[:60]}..."
        )

        return task

    def _extract_deadline(self, sentence: str) -> str:
        deadline_patterns = [
            (re.compile(p, re.IGNORECASE), label)
            for p, label in DEADLINE_PATTERNS
        ]
        for pattern, dtype in deadline_patterns:
            match = pattern.search(sentence)
            if match:
                return match.group(0)
        return None

    def _assess_priority(self, sentence: str) -> str:
        for p in HIGH_PRIORITY_SIGNALS:
            if re.search(p, sentence, re.IGNORECASE):
                return "high"
        for p in LOW_PRIORITY_SIGNALS:
            if re.search(p, sentence, re.IGNORECASE):
                return "low"
        return "medium"

    def _determine_assignee(self, sentence: str, segment: dict) -> str:
        speaker = segment.get("speaker", "UNKNOWN")

        self_patterns = [
            r"\b(i'll|i will|i am going to|i'm going to|let me)\b"
        ]
        for p in self_patterns:
            if re.search(p, sentence, re.IGNORECASE):
                return speaker

        delegation_patterns = [
            r"\b(can you|could you|would you|you need to|you should)\b"
        ]
        for p in delegation_patterns:
            if re.search(p, sentence, re.IGNORECASE):
                return f"{speaker}→DELEGATE"

        return speaker
