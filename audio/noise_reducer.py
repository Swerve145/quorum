# spectral noise reduction using noisereduce
import numpy as np
import noisereduce as nr
from pydub import AudioSegment
from utils.logger import setup_logger
from config import NOISE_REDUCTION, AUDIO_SETTINGS

logger = setup_logger("noise_reducer")


def audio_segment_to_numpy(audio_segment):
    samples = np.array(audio_segment.get_array_of_samples())
    
    samples = samples.astype(np.float32) / 32768.0
    
    logger.debug(f"Converted audio to numpy: {len(samples)} samples")
    
    return samples


def numpy_to_audio_segment(samples, sample_rate):
    samples_int = (samples * 32768.0).astype(np.int16)
    
    audio_segment = AudioSegment(
        samples_int.tobytes(),
        frame_rate=sample_rate,
    )
    
    return audio_segment


def reduce_noise(audio_segment):
    # Applies spectral gating noise reduction to an audio segment.
    sample_rate = audio_segment.frame_rate
    
    logger.info("Starting noise reduction...")
    logger.info(f"Audio duration: {len(audio_segment) / 1000:.1f}s")
    logger.info(f"Stationary noise mode: {NOISE_REDUCTION['stationary']}")
    
    samples = audio_segment_to_numpy(audio_segment)
    
    pre_rms = np.sqrt(np.mean(samples ** 2))
    logger.info(f"Pre-reduction RMS energy: {pre_rms:.6f}")
    
    try:
        reduced_samples = nr.reduce_noise(
            y=samples,
            sr=sample_rate,
            stationary=NOISE_REDUCTION["stationary"],
            prop_decrease=NOISE_REDUCTION["prop_decrease"],
        )
    except Exception as e:
        logger.error(f"Noise reduction failed: {e}")
        logger.warning("Returning original audio without noise reduction")
        return audio_segment
    
    post_rms = np.sqrt(np.mean(reduced_samples ** 2))
    logger.info(f"Post-reduction RMS energy: {post_rms:.6f}")
    
    reduction_percent = ((pre_rms - post_rms) / pre_rms) * 100 if pre_rms > 0 else 0
    logger.info(f"Energy reduction: {reduction_percent:.1f}%")
    
    result = numpy_to_audio_segment(reduced_samples, sample_rate)
    
    logger.info("Noise reduction complete")
    
    # TODO: might want to try different prop_decrease values
    return result
