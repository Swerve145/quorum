# main.py — entry point, runs the pipeline
import sys
import os
import time
from audio.preprocessor import preprocess_audio
from transcription.transcriber import Transcriber
from utils.logger import setup_logger
from config import OUTPUT_DIR

logger = setup_logger("main")

def run_pipeline(audio_path, model_size=None, domain_terms=None):
    """Executes the full Stage 1 pipeline: audio pre-processing followed"""
    logger.info("=" * 60)
    logger.info("QUORUM - Meeting Intelligence Pipeline")
    logger.info("=" * 60)
    logger.info(f"Input: {audio_path}")
    
    pipeline_start = time.time()
    
    # PHASE 1: Audio Pre-Processing
    logger.info("\n>>> PHASE 1: Audio Pre-Processing")
    preprocess_start = time.time()
    
    preprocess_result = preprocess_audio(audio_path)
    chunks = preprocess_result["chunks"]
    
    preprocess_time = time.time() - preprocess_start
    logger.info(f"Pre-processing completed in {preprocess_time:.1f}s")
    
    # PHASE 2: Transcription
    logger.info("\n>>> PHASE 2: Transcription")
    transcribe_start = time.time()
    
    transcriber = Transcriber(model_size=model_size)
    transcript_result = transcriber.transcribe(chunks, domain_terms=domain_terms)
    
    transcribe_time = time.time() - transcribe_start
    logger.info(f"Transcription completed in {transcribe_time:.1f}s")
    
    # OUTPUT: Save transcript to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "transcript.txt")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("QUORUM - Meeting Transcript\n")
        f.write("=" * 40 + "\n")
        f.write(f"Source: {audio_path}\n")
        f.write(f"Model: {transcript_result['model_size']}\n")
        f.write(f"Confidence: {transcript_result['avg_confidence']:.3f}\n")
        f.write("=" * 40 + "\n\n")
        f.write(transcript_result["clean_text"])
    
    logger.info(f"Transcript saved to: {output_path}")
    
    # PIPELINE SUMMARY
    total_time = time.time() - pipeline_start
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Total time: {total_time:.1f}s")
    logger.info(f"    Pre-processing: {preprocess_time:.1f}s")
    logger.info(f"    Transcription:  {transcribe_time:.1f}s")
    logger.info(f"  Chunks processed: {len(chunks)}")
    logger.info(f"  Transcript length: {len(transcript_result['clean_text'])} chars")
    logger.info(f"  Avg confidence: {transcript_result['avg_confidence']:.3f}")
    logger.info(f"  Output: {output_path}")
    logger.info("=" * 60)
    
    return {
        "preprocess": preprocess_result,
        "transcript": transcript_result,
        "timing": {
            "preprocess_s": preprocess_time,
            "transcribe_s": transcribe_time,
            "total_s": total_time,
        },
        "output_path": output_path,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <audio_file>")
        print("Example: python main.py meeting.mp3")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)
    
    result = run_pipeline(audio_file)
    
    print("\n" + "=" * 60)
    print("TRANSCRIPT:")
    print("=" * 60)
    print(result["transcript"]["clean_text"])
