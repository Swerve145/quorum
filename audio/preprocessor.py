# orchestrates the audio pre-processing pipeline
import os
from audio.format_converter import convert_audio
from audio.normaliser import normalise_audio
from audio.noise_reducer import reduce_noise
from audio.silence_detector import detect_silent_regions, split_at_silences
from utils.logger import setup_logger
from config import OUTPUT_DIR

logger = setup_logger("preprocessor")


def preprocess_audio(input_path):
    # Runs the full audio pre-processing pipeline:
    logger.info("=" * 50)
    logger.info("STARTING AUDIO PRE-PROCESSING PIPELINE")
    logger.info("=" * 50)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logger.info("[1/4] Converting audio format...")
    converted_path = convert_audio(
        input_path,
        output_path=os.path.join(OUTPUT_DIR, "converted.wav")
    )
    
    # Load the converted audio for the remaining stages
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(converted_path)
    logger.info(f"[1/4] Format conversion complete. Duration: {len(audio) / 1000:.1f}s")
    
    logger.info("[2/4] Normalising volume levels...")
    audio = normalise_audio(audio)
    logger.info("[2/4] Normalisation complete")
    
    logger.info("[3/4] Reducing background noise...")
    #audio = reduce_noise(audio)
    #logger.info("[3/4] Noise reduction complete")
    
    logger.info("[4/4] Detecting silences and splitting into chunks...")
    silent_regions = detect_silent_regions(audio)
    chunks = split_at_silences(audio, silent_regions)
    logger.info(f"[4/4] Chunking complete. Produced {len(chunks)} chunks")
    
    logger.info("=" * 50)
    logger.info("PRE-PROCESSING PIPELINE COMPLETE")
    logger.info(f"  Input: {input_path}")
    logger.info(f"  Duration: {len(audio) / 1000:.1f}s")
    logger.info(f"  Chunks produced: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        duration = (chunk['end_ms'] - chunk['start_ms']) / 1000
        logger.info(f"    Chunk {i+1}: {duration:.1f}s")
    logger.info("=" * 50)
    
    return {
        "chunks": chunks,
        "cleaned_audio": audio,
        "original_path": input_path,
        "converted_path": converted_path,
    }
