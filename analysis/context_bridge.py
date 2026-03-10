# post-processing bridge: uses summary decisions to adjust task confidence
import re
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ContextBridge:
    """Post-processing bridge between summariser and task extractor."""

    def __init__(self, config=None):
        self.config = config or {}

        # How much to boost confidence for decision-related tasks
        self.boost_amount = self.config.get(
            "context_boost", 0.08
        )
        # Threshold below which we check for decision relevance
        self.rescue_threshold = self.config.get(
            "rescue_threshold", 0.45
        )
        # Minimum similarity to count as decision-related
        self.min_relevance = self.config.get(
            "min_relevance", 0.15
        )

        logger.info("ContextBridge initialised (post-processing mode)")

    def _extract_decision_keywords(self, decisions):
        stopwords = {
            "the", "a", "an", "to", "of", "in", "for", "and",
            "or", "but", "is", "are", "was", "were", "we", "i",
            "they", "it", "that", "this", "with", "on", "at",
            "by", "from", "be", "has", "have", "had", "do",
            "does", "did", "will", "would", "could", "should",
            "let", "lets", "go", "going", "agreed", "decided",
            "based", "about", "been", "not", "no", "yes",
        }

        per_decision = []
        all_keywords = set()

        for decision in decisions:
            text = decision.get("text", "").lower()
            # Extract words, remove short ones and stopwords
            words = re.findall(r"[a-z]+", text)
            keywords = {
                w for w in words
                if len(w) > 2 and w not in stopwords
            }
            per_decision.append(keywords)
            all_keywords.update(keywords)

        logger.info(
            f"Extracted keywords from {len(decisions)} decisions: "
            f"{all_keywords}"
        )

        return per_decision, all_keywords

    def _calculate_relevance(self, text, decision_keywords_list,
                              all_keywords):
        """
        Score how relevant a sentence is to the known decisions.

        Returns a float between 0 and 1 based on keyword overlap.
        """
        words = set(re.findall(r"[a-z]+", text.lower()))

        if not all_keywords:
            return 0.0

        # Count overlapping keywords
        overlap = words & all_keywords
        relevance = len(overlap) / len(all_keywords)

        return min(relevance, 1.0)

    def apply_context(self, tasks, summary_output, aligned_segments,
                       task_extractor):
        """
        Post-process task extraction results using summary context.

        Args:
            tasks: list of task dicts from the extractor
            summary_output: dict from Summariser.summarise()
            aligned_segments: original aligned segments
            task_extractor: the extractor instance (for
                rescoring borderline sentences)

        Returns:
            dict with:
                - tasks: updated task list (boosted + rescued)
                - context_metadata: what the bridge did
        """
        if not summary_output or not summary_output.get("decisions"):
            logger.info("No decisions available — skipping context")
            return {
                "tasks": tasks,
                "context_metadata": {"applied": False},
            }

        decisions = summary_output["decisions"]
        decision_kw_list, all_kw = self._extract_decision_keywords(
            decisions
        )

        boosted_count = 0
        for task in tasks:
            source_text = task.get("task_text", "")
            relevance = self._calculate_relevance(
                source_text, decision_kw_list, all_kw
            )

            if relevance >= self.min_relevance:
                old_conf = task.get("confidence", 0)
                new_conf = min(old_conf + self.boost_amount, 1.0)
                task["confidence"] = round(new_conf, 4)
                task["context_boosted"] = True
                task["decision_relevance"] = round(relevance, 4)
                boosted_count += 1

        logger.info(f"Boosted {boosted_count}/{len(tasks)} tasks")

        # Find segments that weren't classified as tasks
        task_starts = {
            t["source_segment"]["start"] for t in tasks
        }
        non_task_segments = [
            seg for seg in aligned_segments
            if seg["start"] not in task_starts
        ]

        rescued = []
        for seg in non_task_segments:
            relevance = self._calculate_relevance(
                seg.get("text", ""), decision_kw_list, all_kw
            )

            if relevance >= self.min_relevance:
                # This sentence relates to a decision but wasn't
                # flagged as a task — re-score it with lower threshold
                raw_conf = self._get_raw_confidence(
                    seg, task_extractor
                )

                if raw_conf and raw_conf >= self.rescue_threshold:
                    rescued_task = {
                        "task_text": seg.get("text", ""),
                        "speaker": seg.get("speaker", "UNKNOWN"),
                        "confidence": round(
                            raw_conf + self.boost_amount, 4
                        ),
                        "source_segment": seg,
                        "context_rescued": True,
                        "decision_relevance": round(relevance, 4),
                    }
                    rescued.append(rescued_task)

        logger.info(f"Rescued {len(rescued)} borderline sentences")

        all_tasks = tasks + rescued
        all_tasks.sort(key=lambda t: t["source_segment"]["start"])

        context_metadata = {
            "applied": True,
            "decisions_used": len(decisions),
            "keywords": list(all_kw),
            "tasks_boosted": boosted_count,
            "tasks_rescued": len(rescued),
        }

        return {
            "tasks": all_tasks,
            "context_metadata": context_metadata,
        }

    def _get_raw_confidence(self, segment, task_extractor):
        try:
            # Run the extractor on just this one segment
            # with a very low threshold so we get the score
            # even for borderline cases
            original_threshold = task_extractor.min_confidence
            task_extractor.min_confidence = 0.0

            result = task_extractor.extract([segment])

            # Restore threshold
            task_extractor.min_confidence = original_threshold

            if result:
                return result[0].get("confidence", 0)
            return None

        except Exception as e:
            logger.error(f"Rescue scoring failed: {e}")
            return None
