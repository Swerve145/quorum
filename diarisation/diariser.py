# diarisation/diariser.py
# Orchestrates the full diarisation pipeline:
# pyannote engine → embedding extraction → speaker merging.
# Single entry point for the rest of the application.

import logging
from diarisation.pyannote_engine import PyannoteEngine
from diarisation.embedding_extractor import EmbeddingExtractor
from diarisation.speaker_merger import SpeakerMerger

logger = logging.getLogger(__name__)


class Diariser:
    """Top-level diarisation interface. Runs the full pipeline"""

    def __init__(self, auth_token: str = None,
                 num_speakers: int = None,
                 similarity_threshold: float = 0.75,
                 overlap_tolerance: float = 0.5):
        """
        auth_token: HuggingFace token for pyannote access.
        num_speakers: optional speaker count hint for pyannote.
        similarity_threshold: cosine similarity threshold for merging.
        overlap_tolerance: max allowed overlap before blocking merge.
        """
        self.engine = PyannoteEngine(
            auth_token=auth_token,
            num_speakers=num_speakers
        )
        self.extractor = EmbeddingExtractor()
        self.merger = SpeakerMerger(
            similarity_threshold=similarity_threshold,
            overlap_tolerance=overlap_tolerance
        )

    def diarise(self, audio_path: str) -> dict:
        """Run the full diarisation pipeline on an audio file."""
        # Stage 1 — raw diarisation
        logger.info("Step 1/3: Running pyannote diarisation...")
        raw_segments = self.engine.diarise(audio_path)
        raw_count = len(set(s["speaker"] for s in raw_segments))
        logger.info(f"  Raw output: {len(raw_segments)} segments, "
                     f"{raw_count} speakers")

        # Stage 2 — extract embeddings
        logger.info("Step 2/3: Extracting speaker embeddings...")
        speaker_embeddings = self.extractor.extract(
            raw_segments, self.engine.embeddings
        )

        # Stage 3 — merge over-segmented speakers
        logger.info("Step 3/3: Running speaker merger...")
        merged_segments, speaker_map = self.merger.merge(
            raw_segments, speaker_embeddings
        )
        final_count = len(set(s["speaker"] for s in merged_segments))

        logger.info(
            f"Diarisation complete: {raw_count} -> {final_count} speakers "
            f"({raw_count - final_count} merged)"
        )

        return {
            "segments": merged_segments,
            "speaker_map": speaker_map,
            "num_speakers": final_count,
            "embeddings": speaker_embeddings
        }
