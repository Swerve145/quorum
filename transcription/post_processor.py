# cleans up raw Whisper output
import re
from utils.logger import setup_logger
from config import POST_PROCESSING

logger = setup_logger("post_processor")


def remove_stutters(text):
    # Detects and removes repeated words and short phrases that Whisper
    if not POST_PROCESSING["remove_stutters"]:
        return text
    
    max_window = POST_PROCESSING["max_repeat_window"]
    original_text = text
    
    # Matches any word that appears two or more times in a row
    # \b ensures we match whole words, not parts of words
    text = re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', text, flags=re.IGNORECASE)
    
    for phrase_length in range(2, max_window + 1):
        # Build a pattern that matches a phrase of N words repeated consecutively
        # E.g. for phrase_length=2: captures "I think" followed by " I think"
        word_pattern = r'(\b(?:\w+\s+){' + str(phrase_length - 1) + r'}\w+\b)'
        repeat_pattern = word_pattern + r'(\s+\1)+'
        text = re.sub(repeat_pattern, r'\1', text, flags=re.IGNORECASE)
    
    if text != original_text:
        logger.info("Removed stutters from transcript")
        logger.debug(f"  Before: ...{original_text[:100]}...")
        logger.debug(f"  After:  ...{text[:100]}...")
    
    return text


def fix_punctuation(text):
    # Applies rule-based punctuation corrections to the transcript.
    original_text = text
    
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    text = re.sub(r'([.!?])\s*(\w)', lambda m: f"{m.group(1)} {m.group(2).upper()}", text)
    
    text = re.sub(r'\s+[.,;:]\s+', ' ', text)
    
    text = re.sub(r'\s{2,}', ' ', text)
    
    if text:
        text = text[0].upper() + text[1:]
    
    if text != original_text:
        logger.info("Applied punctuation corrections")
    
    return text.strip()


def apply_domain_substitutions(text, extra_terms=None):
    # Replaces commonly misheard words with their correct forms.
    # Merge config terms with any extra terms provided for this session
    terms = dict(POST_PROCESSING["domain_terms"])
    if extra_terms:
        terms.update(extra_terms)
    
    if not terms:
        logger.debug("No domain substitutions configured")
        return text
    
    substitution_count = 0
    
    for wrong, correct in terms.items():
        # Case-insensitive search, but we need to count matches
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        matches = pattern.findall(text)
        
        if matches:
            text = pattern.sub(correct, text)
            substitution_count += len(matches)
            logger.debug(f"  Replaced '{wrong}' -> '{correct}' ({len(matches)} times)")
    
    if substitution_count > 0:
        logger.info(f"Applied {substitution_count} domain substitution(s)")
    
    return text


def post_process_transcript(text, extra_terms=None):
    # Runs the full post-processing pipeline on a transcript.
    logger.info("Starting post-processing...")
    logger.info(f"Input length: {len(text)} characters")
    
    text = remove_stutters(text)
    
    text = fix_punctuation(text)
    
    text = apply_domain_substitutions(text, extra_terms)
    
    logger.info(f"Post-processing complete. Output length: {len(text)} characters")
    
    return text
