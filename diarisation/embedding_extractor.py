# diarisation/embedding_extractor.py
# Organises speaker embeddings from the pyannote pipeline
# into a per-speaker dictionary. If pre-computed embeddings
# are available from DiarizeOutput, uses those directly.
# Otherwise, computes average embeddings from segment-level data.

import logging
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """Maps speaker labels to their voice embedding vectors."""

    def extract(self, segments: list, embeddings: np.ndarray = None) -> dict:
        """Build a dictionary mapping each speaker label to"""
        # Get unique speakers in the order they first appear
        seen = set()
        speaker_order = []
        for seg in segments:
            if seg["speaker"] not in seen:
                seen.add(seg["speaker"])
                speaker_order.append(seg["speaker"])

        logger.info(f"Found {len(speaker_order)} unique speakers: {speaker_order}")

        if embeddings is not None:
            return self._from_precomputed(speaker_order, embeddings)
        else:
            logger.warning(
                "No pre-computed embeddings available. "
                "Speaker merger will have limited accuracy."
            )
            return self._empty_embeddings(speaker_order)

    def _from_precomputed(self, speaker_order: list, embeddings: np.ndarray) -> dict:
        if len(speaker_order) != embeddings.shape[0]:
            logger.warning(
                f"Speaker count ({len(speaker_order)}) doesn't match "
                f"embedding count ({embeddings.shape[0]}). "
                "Mapping as many as possible."
            )

        speaker_embeddings = {}
        for i, speaker in enumerate(speaker_order):
            if i < embeddings.shape[0]:
                speaker_embeddings[speaker] = embeddings[i]
                logger.info(
                    f"  {speaker} -> embedding dim {embeddings[i].shape[0]}"
                )

        return speaker_embeddings

    def _empty_embeddings(self, speaker_order: list) -> dict:
        logger.warning("Returning empty embeddings — merging will be limited.")
        return {speaker: None for speaker in speaker_order}
