# volume normalisation using peak/RMS analysis
import numpy as np
from pydub import AudioSegment
from utils.logger import setup_logger
from config import AUDIO_SETTINGS

logger = setup_logger("normaliser")


def get_audio_stats(audio_segment):
    stats = {
        "dBFS": audio_segment.dBFS,
        "max_dBFS": audio_segment.max_dBFS,
        "duration_s": len(audio_segment) / 1000.0,
    }
    logger.debug(f"Audio stats: {stats}")
    return stats


def normalise_audio(audio_segment):
    """Normalises an audio segment to a target dB level."""
    target_db = AUDIO_SETTINGS["normalisation_target_db"]
    
    current_db = audio_segment.dBFS
    logger.info(f"Current average loudness: {current_db:.1f} dBFS")
    logger.info(f"Target loudness: {target_db:.1f} dBFS")
    
    gain_change = target_db - current_db
    logger.info(f"Applying gain change: {gain_change:+.1f} dB")
    
    normalised = audio_segment.apply_gain(gain_change)
    
    if normalised.max_dBFS > 0:
        logger.warning(
            f"Clipping detected after normalisation (peak: {normalised.max_dBFS:.1f} dBFS). "
            f"Reducing gain to prevent distortion."
        )
        # Pull back just enough to eliminate clipping
        normalised = normalised.apply_gain(-normalised.max_dBFS)
    
    logger.info(f"Normalised loudness: {normalised.dBFS:.1f} dBFS")
    
    return normalised
