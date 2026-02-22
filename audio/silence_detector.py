# detects silences and splits audio into chunks
import numpy as np
from pydub import AudioSegment
from utils.logger import setup_logger
from config import SILENCE_DETECTION

logger = setup_logger("silence_detector")

def detect_silent_regions(audio_segment):
    # Scans through the audio and identifies regions where the volume
    threshold_db = SILENCE_DETECTION["silence_threshold_db"]
    min_silence_ms = int(SILENCE_DETECTION["min_silence_duration"] * 1000)
    
    # without being so small that brief dips get flagged
    window_ms = 50
    
    logger.info(f"Scanning for silence (threshold: {threshold_db} dB, "
                f"min duration: {min_silence_ms}ms)")
    
    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32)
    sample_rate = audio_segment.frame_rate
    
    window_samples = int(sample_rate * window_ms / 1000)
    step_samples = int(sample_rate * step_ms / 1000)
    
    silent_regions = []
    silence_start = None
    
    position = 0
    while position + window_samples <= len(samples):
        window = samples[position:position + window_samples]
        
        rms = np.sqrt(np.mean(window ** 2))
        
        if rms > 0:
            db = 20 * np.log10(rms / 32768.0)
        else:
        
        if db < threshold_db:
            # We're in a silent region
            if silence_start is None:
                silence_start = position
        else:
            # We've left a silent region — check if it was long enough
            if silence_start is not None:
                silence_end = position
                duration_ms = ((silence_end - silence_start) / sample_rate) * 1000
                
                if duration_ms >= min_silence_ms:
                    start_ms = (silence_start / sample_rate) * 1000
                    end_ms = (silence_end / sample_rate) * 1000
                    silent_regions.append((start_ms, end_ms))
                
                silence_start = None
        
        position += step_samples
    
    # Handle case where audio ends during a silent region
    if silence_start is not None:
        silence_end = len(samples)
        duration_ms = ((silence_end - silence_start) / sample_rate) * 1000
        if duration_ms >= min_silence_ms:
            start_ms = (silence_start / sample_rate) * 1000
            end_ms = (silence_end / sample_rate) * 1000
            silent_regions.append((start_ms, end_ms))
    
    logger.info(f"Found {len(silent_regions)} silent regions")
    for i, (start, end) in enumerate(silent_regions):
        logger.debug(f"  Silence {i+1}: {start:.0f}ms - {end:.0f}ms "
                     f"({end - start:.0f}ms)")
    
    return silent_regions

def split_at_silences(audio_segment, silent_regions):
    # Splits the audio into chunks at the detected silence boundaries.
    max_chunk_ms = SILENCE_DETECTION["max_chunk_duration"] * 1000
    min_chunk_ms = SILENCE_DETECTION["min_chunk_duration"] * 1000
    total_duration_ms = len(audio_segment)
    
    logger.info(f"Splitting audio ({total_duration_ms / 1000:.1f}s) into chunks")
    logger.info(f"Constraints: max {max_chunk_ms / 1000:.0f}s, "
                f"min {min_chunk_ms / 1000:.0f}s per chunk")
    
    split_points = []
    for start, end in silent_regions:
        midpoint = (start + end) / 2
        split_points.append(midpoint)
    
    chunks = []
    previous_end = 0
    
    for split_point in split_points:
        if split_point <= previous_end:
            continue
        
        chunk_start = previous_end
        chunk_end = split_point
        
        chunks.append({
            "start_ms": chunk_start,
            "end_ms": chunk_end,
        })
        previous_end = chunk_end
    
    # Don't forget the final chunk after the last split point
    if previous_end < total_duration_ms:
        chunks.append({
            "start_ms": previous_end,
            "end_ms": total_duration_ms,
        })
    
    merged_chunks = []
    for chunk in chunks:
        duration = chunk["end_ms"] - chunk["start_ms"]
        
        if merged_chunks and duration < min_chunk_ms:
            # Merge with previous chunk
            merged_chunks[-1]["end_ms"] = chunk["end_ms"]
            logger.debug(
                f"Merged short chunk ({duration:.0f}ms) with previous"
            )
        else:
            merged_chunks.append(chunk)
    
    final_chunks = []
    for chunk in merged_chunks:
        duration = chunk["end_ms"] - chunk["start_ms"]
        
        if duration > max_chunk_ms:
            # Split into roughly equal parts
            num_splits = int(np.ceil(duration / max_chunk_ms))
            split_duration = duration / num_splits
            
            logger.debug(
                f"Force-splitting long chunk ({duration / 1000:.1f}s) "
                f"into {num_splits} parts"
            )
            
            for i in range(num_splits):
                sub_start = chunk["start_ms"] + (i * split_duration)
                sub_end = chunk["start_ms"] + ((i + 1) * split_duration)
                final_chunks.append({
                    "start_ms": sub_start,
                    "end_ms": min(sub_end, chunk["end_ms"]),
                })
        else:
            final_chunks.append(chunk)
    
    for chunk in final_chunks:
        start = int(chunk["start_ms"])
        end = int(chunk["end_ms"])
        chunk["audio"] = audio_segment[start:end]
    
    logger.info(f"Produced {len(final_chunks)} chunks:")
    for i, chunk in enumerate(final_chunks):
        duration = (chunk["end_ms"] - chunk["start_ms"]) / 1000
        logger.info(f"  Chunk {i+1}: {chunk['start_ms'] / 1000:.1f}s - "
                    f"{chunk['end_ms'] / 1000:.1f}s ({duration:.1f}s)")
    
    return final_chunks
