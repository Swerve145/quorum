# config.py — central settings for Quorum
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

AUDIO_SETTINGS = {
    "target_sample_rate": 16000,       # Whisper expects 16kHz
    "target_format": "wav",            # Output format after conversion
    "normalisation_target_db": -20.0,  # Target dB level for normalisation
}

NOISE_REDUCTION = {
    "stationary": True,                # Assume stationary background noise
    "prop_decrease": 1.0,              # Proportion of noise to reduce (0.0 to 1.0)
}

SILENCE_DETECTION = {
    "min_silence_duration": 0.5,       # Minimum silence length in seconds to count as a pause
    "silence_threshold_db": -40,       # dB below which audio is considered silence
    "max_chunk_duration": 30,          # Maximum chunk length in seconds for Whisper
    "min_chunk_duration": 5,           # Minimum chunk length to avoid tiny fragments
}

WHISPER_SETTINGS = {
    "model_size": "base",              # Options: tiny, base, small, medium
    "language": "en",                  # Language code
    "word_timestamps": True,           # Enable word-level timestamps
}

POST_PROCESSING = {
    "remove_stutters": True,           # Remove repeated words/phrases
    "max_repeat_window": 3,            # How many consecutive tokens to check for repeats
    "domain_terms": {},                # Custom substitutions e.g. {"wisper": "Whisper"}
}
