# orchestrates summariser -> context bridge -> task extractor
import os
from analysis.summariser import Summariser
from analysis.context_bridge import ContextBridge
from analysis.task_extractor import TaskExtractor, TaskExtractorV2
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Analyser:
    """Orchestrates meeting analysis."""

    def __init__(self, config=None):
        self.config = config or {}

        self.summariser = Summariser(config=self.config)

        self.context_bridge = ContextBridge(config=self.config)

        checkpoint_dir = self.config.get(
            "task_model_checkpoint",
            os.path.join("models", "checkpoints", "task_v2")
        )

        if os.path.exists(checkpoint_dir):
            logger.info(
                f"Checkpoint found at {checkpoint_dir} — using v2"
            )
            self.task_extractor = TaskExtractorV2(
                checkpoint_dir=checkpoint_dir,
                config=self.config
            )
            self.extractor_version = "v2_distilbert"
        else:
            logger.info(
                "No checkpoint found — falling back to v1 rule-based"
            )
            self.task_extractor = TaskExtractor(config=self.config)
            self.extractor_version = "v1_rule_based"

        logger.info(
            f"Analyser initialised — full Stage 4 pipeline "
            f"(extractor: {self.extractor_version})"
        )

    def analyse(self, aligned_segments):
        """Run the full analysis pipeline."""
        logger.info(
            f"Starting analysis on {len(aligned_segments)} segments"
        )

        summary = None
        try:
            summary = self.summariser.summarise(aligned_segments)
            logger.info(
                f"Summarisation complete: "
                f"{summary['metadata']['decision_count']} decisions, "
                f"{summary['metadata']['topic_count']} topics"
            )
        except Exception as e:
            logger.error(
                f"Summarisation failed: {e}. "
                f"Task extraction will run without context."
            )

        tasks = self.task_extractor.extract(aligned_segments)

        context_applied = False
        context_metadata = {}

        if summary and summary.get("decisions"):
            try:
                bridge_result = self.context_bridge.apply_context(
                    tasks, summary, aligned_segments,
                    self.task_extractor
                )
                tasks = bridge_result["tasks"]
                context_metadata = bridge_result["context_metadata"]
                context_applied = context_metadata.get("applied", False)
            except Exception as e:
                logger.error(f"Context bridge failed: {e}")

        tasks.sort(key=lambda t: t["source_segment"]["start"])

        result = {
            "tasks": tasks,
            "summary": summary,
            "metadata": {
                "total_segments": len(aligned_segments),
                "tasks_found": len(tasks),
                "extractor_version": self.extractor_version,
                "context_applied": context_applied,
                "context_details": context_metadata,
                "summary_available": summary is not None,
            },
        }

        logger.info(
            f"Analysis complete: {len(tasks)} tasks, "
            f"context_applied={context_applied}"
        )

        return result
