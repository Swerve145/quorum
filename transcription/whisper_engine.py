# whisper model loading and transcription
import whisper
import os
import numpy as np
from pydub import AudioSegment
from utils.logger import setup_logger
from config import WHISPER_SETTINGS

logger = setup_logger("whisper_engine")


class WhisperEngine:
    """Wraps the Whisper model with loading, transcription, and"""
    
    def __init__(self, model_size=None):
        self.model_size = model_size or WHISPER_SETTINGS["model_size"]
        self.model = None
        
        logger.info(f"Initialising Whisper engine (model: {self.model_size})")
        self._load_model()
    
    def _load_model(self):
        logger.info(f"Loading Whisper '{self.model_size}' model...")
        
        try:
            self.model = whisper.load_model(self.model_size)
            logger.info(f"Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_chunk(self, audio_chunk):
        # Transcribes a single audio chunk and extracts detailed results
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")
        
        audio_segment = audio_chunk["audio"]
        chunk_start = audio_chunk["start_ms"]
        chunk_end = audio_chunk["end_ms"]
        
        duration_s = (chunk_end - chunk_start) / 1000
        logger.info(f"Transcribing chunk: {chunk_start / 1000:.1f}s - "
                    f"{chunk_end / 1000:.1f}s ({duration_s:.1f}s)")
        
        # Whisper handles file loading internally and correctly reads
        # sample rate from the WAV header. Passing raw numpy arrays
        # can cause silent failures if the format isn't exactly right.
        import tempfile
        
        temp_path = os.path.join(tempfile.gettempdir(), "quorum_chunk.wav")
        audio_segment.export(temp_path, format="wav")
        
        try:
            result = self.model.transcribe(
                temp_path,
                language=WHISPER_SETTINGS["language"],
                word_timestamps=WHISPER_SETTINGS["word_timestamps"],
            )
        except Exception as e:
            logger.error(f"Transcription failed for chunk at {chunk_start}ms: {e}")
            return {
                "text": "",
                "segments": [],
                "words": [],
                "chunk_start_ms": chunk_start,
                "chunk_end_ms": chunk_end,
                "avg_confidence": 0.0,
            }
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        segments = []
        all_words = []
        confidence_scores = []
        
        for seg in result.get("segments", []):
            segment_data = {
                "text": seg["text"].strip(),
                # Offset timestamps to position in original recording
                "start_ms": chunk_start + (seg["start"] * 1000),
                "end_ms": chunk_start + (seg["end"] * 1000),
                "confidence": seg.get("avg_logprob", 0.0),
            }
            segments.append(segment_data)
            confidence_scores.append(segment_data["confidence"])
            
            for word in seg.get("words", []):
                word_data = {
                    "text": word["word"].strip(),
                    "start_ms": chunk_start + (word["start"] * 1000),
                    "end_ms": chunk_start + (word["end"] * 1000),
                    "probability": word.get("probability", 0.0),
                }
                all_words.append(word_data)
        
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores else 0.0
        )
        
        logger.info(f"Transcribed: '{result.get('text', '').strip()[:80]}...'")
        logger.info(f"Segments: {len(segments)}, Words: {len(all_words)}, "
                    f"Avg confidence: {avg_confidence:.3f}")
        
        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "words": all_words,
            "chunk_start_ms": chunk_start,
            "chunk_end_ms": chunk_end,
            "avg_confidence": avg_confidence,
        }
    
    def transcribe_all_chunks(self, chunks):
        # Transcribes a list of audio chunks sequentially and combines
        logger.info(f"Starting transcription of {len(chunks)} chunks")
        
        all_segments = []
        all_words = []
        all_text = []
        chunk_results = []
        all_confidences = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"--- Chunk {i+1}/{len(chunks)} ---")
            result = self.transcribe_chunk(chunk)
            
            chunk_results.append(result)
            all_text.append(result["text"])
            all_segments.extend(result["segments"])
            all_words.extend(result["words"])
            
            if result["avg_confidence"] != 0.0:
                all_confidences.append(result["avg_confidence"])
        
        full_text = " ".join(all_text)
        avg_confidence = (
            sum(all_confidences) / len(all_confidences)
            if all_confidences else 0.0
        )
        
        logger.info(f"Transcription complete. Total length: {len(full_text)} chars")
        logger.info(f"Total segments: {len(all_segments)}, "
                    f"Total words: {len(all_words)}")
        logger.info(f"Overall avg confidence: {avg_confidence:.3f}")
        
        return {
            "full_text": full_text,
            "segments": all_segments,
            "words": all_words,
            "chunk_results": chunk_results,
            "avg_confidence": avg_confidence,
        }
