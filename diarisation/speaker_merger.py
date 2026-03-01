# diarisation/speaker_merger.py
# Custom agglomerative speaker merging algorithm.
# Merges over-segmented speaker labels from pyannote
# using cosine similarity on voice embeddings, with
# temporal overlap validation as a merge constraint.
# This is the core original algorithm of Stage 2.

import logging
import numpy as np

logger = logging.getLogger(__name__)


class SpeakerMerger:
    """Merges over-segmented speaker labels by comparing voice"""

    def __init__(self, similarity_threshold: float = 0.75,
                 overlap_tolerance: float = 0.5):
        """
        similarity_threshold: minimum cosine similarity to
            consider merging two speakers. Higher = stricter,
            fewer merges. This is the key tuneable parameter.
        overlap_tolerance: maximum seconds of overlap allowed
            between two speakers before blocking a merge.
            Small tolerance accounts for timestamp imprecision.
        """
        self.similarity_threshold = similarity_threshold
        self.overlap_tolerance = overlap_tolerance

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            logger.warning("Zero-norm embedding detected.")
            return 0.0

        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def build_similarity_matrix(self, speaker_embeddings: dict) -> dict:
        """Compute pairwise cosine similarity between all speakers."""
        speakers = list(speaker_embeddings.keys())
        matrix = {}

        for i, spk_a in enumerate(speakers):
            matrix[spk_a] = {}
            for j, spk_b in enumerate(speakers):
                if i == j:
                    continue
                if speaker_embeddings[spk_a] is None or speaker_embeddings[spk_b] is None:
                    matrix[spk_a][spk_b] = 0.0
                    continue
                sim = self.cosine_similarity(
                    speaker_embeddings[spk_a],
                    speaker_embeddings[spk_b]
                )
                matrix[spk_a][spk_b] = sim

        # Log the matrix for debug
        logger.info("Similarity matrix:")
        for spk_a in speakers:
            for spk_b in speakers:
                if spk_a != spk_b:
                    logger.info(
                        f"  {spk_a} <-> {spk_b}: "
                        f"{matrix[spk_a][spk_b]:.4f}"
                    )

        return matrix

    def check_temporal_overlap(self, segments: list,
                                speaker_a: str, speaker_b: str) -> float:
        """
        Calculate total overlapping time between two speakers.
        If they talk at the same time, they cannot be the
        same person.

        Returns total overlap in seconds.
        """
        segs_a = [s for s in segments if s["speaker"] == speaker_a]
        segs_b = [s for s in segments if s["speaker"] == speaker_b]

        total_overlap = 0.0

        for sa in segs_a:
            for sb in segs_b:
                # Calculate intersection of two time intervals
                overlap_start = max(sa["start"], sb["start"])
                overlap_end = min(sa["end"], sb["end"])

                if overlap_end > overlap_start:
                    total_overlap += overlap_end - overlap_start

        return round(total_overlap, 3)

    def find_best_merge(self, similarity_matrix: dict,
                        segments: list, active_speakers: set) -> tuple:
        """
        Find the pair of active speakers with the highest
        similarity that passes the temporal overlap check.

        Returns (speaker_a, speaker_b, similarity) or
        (None, None, 0.0) if no valid merge exists.
        """
        best_pair = (None, None)
        best_sim = 0.0

        for spk_a in active_speakers:
            for spk_b in active_speakers:
                    continue

                sim = similarity_matrix.get(spk_a, {}).get(spk_b, 0.0)

                if sim < self.similarity_threshold:
                    continue

                if sim <= best_sim:
                    continue

                # Check temporal constraint
                overlap = self.check_temporal_overlap(
                    segments, spk_a, spk_b
                )

                if overlap > self.overlap_tolerance:
                    logger.info(
                        f"  Blocked merge {spk_a} + {spk_b}: "
                        f"{overlap:.2f}s overlap"
                    )
                    continue

                best_pair = (spk_a, spk_b)
                best_sim = sim

        return best_pair[0], best_pair[1], best_sim

    def merge(self, segments: list, speaker_embeddings: dict) -> tuple:
        """Main merging algorithm. Iteratively merges the most"""
        if not speaker_embeddings:
            logger.warning("No embeddings provided — skipping merge.")
            return segments, {}

        # Build similarity matrix
        similarity_matrix = self.build_similarity_matrix(speaker_embeddings)

        # Track which speakers are still active (not yet merged)
        active_speakers = set(speaker_embeddings.keys())
        # Maps every original label to its current label
        speaker_map = {spk: spk for spk in active_speakers}

        logger.info(
            f"Starting merge: {len(active_speakers)} speakers, "
            f"threshold={self.similarity_threshold}"
        )

        merge_count = 0

        while len(active_speakers) > 1:
            spk_a, spk_b, sim = self.find_best_merge(
                similarity_matrix, segments, active_speakers
            )

            if spk_a is None:
                logger.info("No more valid merges above threshold.")
                break

            merge_count += 1
            logger.info(
                f"Merge {merge_count}: {spk_b} -> {spk_a} "
                f"(similarity: {sim:.4f})"
            )

            # Update speaker map — everything that pointed to
            # spk_b now points to spk_a
            for original, current in speaker_map.items():
                if current == spk_b:
                    speaker_map[original] = spk_a

            # Update segments in place
            for seg in segments:
                if seg["speaker"] == spk_b:
                    seg["speaker"] = spk_a

            # Remove merged speaker from active set
            active_speakers.discard(spk_b)

            # Update similarity matrix — spk_a absorbs spk_b's
            # relationships by taking the higher similarity
            for other in active_speakers:
                if other == spk_a:
                    continue
                sim_a = similarity_matrix.get(spk_a, {}).get(other, 0.0)
                sim_b = similarity_matrix.get(spk_b, {}).get(other, 0.0)
                new_sim = min(sim_a, sim_b)
                similarity_matrix[spk_a][other] = new_sim
                similarity_matrix[other][spk_a] = new_sim

        logger.info(
            f"Merging complete: {merge_count} merges performed. "
            f"{len(active_speakers)} speakers remain."
        )

        return segments, speaker_map
