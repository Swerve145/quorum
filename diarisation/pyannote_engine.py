# diarisation/pyannote_engine.py
# Wraps pyannote.audio's speaker diarisation pipeline.
# Takes a path to an audio file, returns raw speaker segments
# with start/end timestamps and speaker labels.
# These segments will be over-segmented — the speaker_merger
# handles consolidation downstream.

import os
import logging
from pyannote import audio
from pyannote.audio import Pipeline
from pydub import AudioSegment
import tempfile


logger = logging.getLogger(__name__)


class PyannoteEngine:
    """Wrapper around pyannote.audio's pre-trained speaker"""

    def __init__(self, auth_token: str = None, num_speakers: int = None):
        self.auth_token = auth_token or os.environ.get("HF_AUTH_TOKEN")
        if not self.auth_token:
            raise ValueError(
                "HuggingFace auth token required. Pass directly or "
                "set HF_AUTH_TOKEN environment variable."
            )
        self.num_speakers = num_speakers
        self.pipeline = None

    def load_model(self):
        logger.info("Loading pyannote diarisation pipeline...")
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=self.auth_token
        )
        logger.info("Pyannote pipeline loaded successfully.")

    def diarise(self, audio_path: str) -> list:
        # Run diarisation on an audio file.
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        resampled_path = tempfile.mktemp(suffix="_16k.wav")
        audio.export(resampled_path, format="wav")
        audio_path = resampled_path

        if self.pipeline is None:
            self.load_model()

        logger.info(f"Running diarisation on: {audio_path}")

        # Build parameters — only pass num_speakers if set
        params = {}
        if self.num_speakers is not None:
            params["num_speakers"] = self.num_speakers
            logger.info(f"Speaker count hint: {self.num_speakers}")

        # Run the pipeline
        diarisation_result = self.pipeline(audio_path, **params)

        # Older pyannote versions return a DiarizeOutput object
        # containing speaker_diarization (Annotation) and
        # speaker_embeddings. We extract the Annotation.
        if hasattr(diarisation_result, 'speaker_diarization'):
            annotation = diarisation_result.speaker_diarization
            self.embeddings = diarisation_result.speaker_embeddings
            logger.info("Extracted annotation from DiarizeOutput. "
                        f"Embeddings shape: {self.embeddings.shape}")
        else:
            annotation = diarisation_result
            self.embeddings = None

        # Extract segments from pyannote's Annotation object
        segments = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            segment = {
                "start": round(turn.start, 3),
                "end": round(turn.end, 3),
                "speaker": speaker
            }
            segments.append(segment)

        logger.info(
            f"Diarisation complete: {len(segments)} segments, "
            f"{len(set(s['speaker'] for s in segments))} speakers detected."
        )

        return segments
