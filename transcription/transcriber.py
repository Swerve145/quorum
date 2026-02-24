# wires Whisper + post-processor together
from transcription.whisper_engine import WhisperEngine
from transcription.post_processor import post_process_transcript
from utils.logger import setup_logger
from config import WHISPER_SETTINGS

logger = setup_logger("transcriber")


class Transcriber:
    """Manages the full transcription pipeline: Whisper inference"""
    
    def __init__(self, model_size=None):
        self.engine = WhisperEngine(model_size=model_size)
        self.model_size = self.engine.model_size
        
        logger.info(f"Transcriber ready (model: {self.model_size})")
    
    def transcribe(self, chunks, domain_terms=None):
        # Runs the full transcription pipeline on a set of audio chunks.
        logger.info("=" * 50)
        logger.info("STARTING TRANSCRIPTION PIPELINE")
        logger.info(f"Chunks to process: {len(chunks)}")
        logger.info(f"Model: {self.model_size}")
        logger.info("=" * 50)
        
        logger.info("[1/2] Running Whisper inference...")
        whisper_result = self.engine.transcribe_all_chunks(chunks)
        
        raw_text = whisper_result["full_text"]
        logger.info(f"[1/2] Raw transcript: {len(raw_text)} characters")
        
        logger.info("[2/2] Running post-processing...")
        clean_text = post_process_transcript(raw_text, extra_terms=domain_terms)
        logger.info(f"[2/2] Cleaned transcript: {len(clean_text)} characters")
        
        if len(raw_text) > 0:
            change_ratio = abs(len(clean_text) - len(raw_text)) / len(raw_text) * 100
            logger.info(f"Post-processing changed text by {change_ratio:.1f}%")
        
        logger.info("=" * 50)
        logger.info("TRANSCRIPTION PIPELINE COMPLETE")
        logger.info(f"  Raw length: {len(raw_text)} chars")
        logger.info(f"  Clean length: {len(clean_text)} chars")
        logger.info(f"  Segments: {len(whisper_result['segments'])}")
        logger.info(f"  Words: {len(whisper_result['words'])}")
        logger.info(f"  Avg confidence: {whisper_result['avg_confidence']:.3f}")
        logger.info("=" * 50)
        
        return {
            "raw_text": raw_text,
            "clean_text": clean_text,
            "segments": whisper_result["segments"],
            "words": whisper_result["words"],
            "chunk_results": whisper_result["chunk_results"],
            "avg_confidence": whisper_result["avg_confidence"],
            "model_size": self.model_size,
        }
