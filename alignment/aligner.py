# alignment/aligner.py
# Merges transcription segments with diarisation segments
# to produce a unified speaker-attributed transcript.
# Uses timestamp overlap to assign each transcribed segment
# to the speaker who was talking at that time.

import logging

logger = logging.getLogger(__name__)

class Aligner:
    """Aligns transcription output with diarisation output"""

    def align(self, transcript_segments: list,
              diarisation_segments: list) -> list:
        """
        Merge transcript and diarisation data.

        transcript_segments: list of dicts from transcriber
            [{"start": 0.0, "end": 2.5, "text": "hello", "confidence": 0.92}, ...]

        diarisation_segments: list of dicts from diariser
            [{"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"}, ...]

        Returns list of aligned segments:
            [{
                "start": 0.0,
                "end": 2.5,
                "text": "hello",
                "speaker": "SPEAKER_00",
                "confidence": 0.92
            }, ...]
        """
        if not transcript_segments:
            logger.warning("No transcript segments to align.")
            return []

        if not diarisation_segments:
            logger.warning("No diarisation segments — assigning UNKNOWN.")
            return [
                {**seg, "speaker": "UNKNOWN"}
                for seg in transcript_segments
            ]

        aligned = []

        for t_seg in transcript_segments:
            speaker = self._find_speaker(t_seg, diarisation_segments)
            # Normalise timestamps to seconds
            if "start_ms" in t_seg:
                start = t_seg["start_ms"] / 1000
                end = t_seg["end_ms"] / 1000
            else:
                start = t_seg["start"]
                end = t_seg["end"]

            aligned_seg = {
                "start": start,
                "end": end,
                "text": t_seg["text"],
                "speaker": speaker,
                "confidence": t_seg.get("confidence", None)
            }
            aligned.append(aligned_seg)

        # Log summary
        speakers_found = set(s["speaker"] for s in aligned)
        unmatched = sum(1 for s in aligned if s["speaker"] == "UNKNOWN")
        logger.info(
            f"Alignment complete: {len(aligned)} segments, "
            f"{len(speakers_found)} speakers, "
            f"{unmatched} unmatched segments."
        )

        return aligned

    def _find_speaker(self, transcript_seg: dict,
                      diarisation_segments: list) -> str:
        """
        Find which speaker has the most temporal overlap
        with a given transcript segment.

        Uses interval intersection: for each diarisation
        segment, calculate how much it overlaps with the
        transcript segment. The speaker with the highest
        total overlap wins.
        """
        # Handle both formats: seconds (from diariser) and
        # milliseconds (from transcriber)
        if "start_ms" in transcript_seg:
            t_start = transcript_seg["start_ms"] / 1000
            t_end = transcript_seg["end_ms"] / 1000
        else:
            t_start = transcript_seg["start"]
            t_end = transcript_seg["end"]

        speaker_overlap = {}

        for d_seg in diarisation_segments:
            # Calculate overlap between transcript and diarisation segment
            overlap_start = max(t_start, d_seg["start"])
            overlap_end = min(t_end, d_seg["end"])

            if overlap_end > overlap_start:
                overlap_duration = overlap_end - overlap_start
                speaker = d_seg["speaker"]
                speaker_overlap[speaker] = (
                    speaker_overlap.get(speaker, 0.0) + overlap_duration
                )

        if not speaker_overlap:
            logger.debug(
                f"No speaker found for segment "
                f"[{t_start:.1f}s - {t_end:.1f}s]"
            )
            return "UNKNOWN"

        # Return speaker with greatest overlap
        best_speaker = max(speaker_overlap, key=speaker_overlap.get)
        return best_speaker

    def format_transcript(self, aligned_segments: list) -> str:
        # Produce a readable speaker-attributed transcript.
        if not aligned_segments:
            return ""

        lines = []
        current_speaker = None
        current_text = []
        current_start = None

        for seg in aligned_segments:
            if seg["speaker"] != current_speaker:
                # Save previous speaker's block
                if current_speaker is not None:
                    lines.append(
                        f"[{current_start:.1f}s] {current_speaker}: "
                        f"{' '.join(current_text)}"
                    )
                # Start new block
                current_speaker = seg["speaker"]
                current_text = [seg["text"]]
                current_start = seg["start"]
            else:
                current_text.append(seg["text"])

        # Don't forget the last block
        if current_speaker is not None:
            lines.append(
                f"[{current_start:.1f}s] {current_speaker}: "
                f"{' '.join(current_text)}"
            )

        return "\n".join(lines)
