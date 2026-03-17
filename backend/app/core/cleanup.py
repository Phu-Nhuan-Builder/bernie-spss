"""
Temp file cleanup utility — prefix-based safe cleanup.
Only cleans files owned by StatWorks (prefixed with TEMP_FILE_PREFIX).
"""
import os
import time
import glob
import logging
import tempfile

logger = logging.getLogger(__name__)

TEMP_FILE_PREFIX = "statworks_"


def clean_temp_files(max_age_seconds: int = 3600) -> int:
    """
    Remove stale temp files with our prefix.
    Returns count of files removed.
    """
    pattern = os.path.join(tempfile.gettempdir(), f"{TEMP_FILE_PREFIX}*")
    removed = 0
    now = time.time()

    for path in glob.glob(pattern):
        try:
            if os.path.isfile(path):
                age = now - os.path.getmtime(path)
                if age > max_age_seconds:
                    os.unlink(path)
                    removed += 1
        except OSError:
            pass

    if removed > 0:
        logger.info(f"Cleaned {removed} stale temp files (age > {max_age_seconds}s)")
    return removed


def make_temp_path(suffix: str) -> str:
    """Create a temp file path with our prefix. Caller must delete."""
    fd, path = tempfile.mkstemp(prefix=TEMP_FILE_PREFIX, suffix=suffix)
    os.close(fd)
    return path
