# converts input audio to 16kHz mono WAV
import os
from pydub import AudioSegment
from utils.logger import setup_logger
from config import AUDIO_SETTINGS

logger = setup_logger("format_converter")


def convert_audio(input_path, output_path=None):
    """Takes an audio file in any common format and converts it to"""
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        raise FileNotFoundError(f"Audio file not found: {input_path}")
    
    logger.info(f"Loading audio file: {input_path}")
    
    file_extension = os.path.splitext(input_path)[1].lower().strip(".")
    
    try:
        audio = AudioSegment.from_file(input_path, format=file_extension)
    except Exception as e:
        logger.error(f"Failed to load audio file: {e}")
        raise
    
    logger.info(
        f"Original: {audio.frame_rate}Hz, "
        f"{audio.channels} channel(s), "
        f"{len(audio) / 1000:.1f}s duration"
    )
    
    if audio.channels > 1:
        logger.info(f"Converting from {audio.channels} channels to mono")
        audio = audio.set_channels(AUDIO_SETTINGS["target_channels"])
    
    if audio.frame_rate != AUDIO_SETTINGS["target_sample_rate"]:
        logger.info(
            f"Resampling from {audio.frame_rate}Hz "
            f"to {AUDIO_SETTINGS['target_sample_rate']}Hz"
        )
        audio = audio.set_frame_rate(AUDIO_SETTINGS["target_sample_rate"])
    
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_converted.wav"
    
    audio.export(output_path, format=AUDIO_SETTINGS["target_format"])
    
    logger.info(f"Converted audio saved to: {output_path}")
    
    return output_path
