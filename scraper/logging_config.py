import logging
from pathlib import Path
import sys


def setup_scraper_logging(level: int = logging.INFO) -> None:
    """Configure scraper logging to always write to logs/scraper.log."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    root_dir = Path(__file__).resolve().parent.parent
    log_dir = root_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "scraper.log"

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = None
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(getattr(handler, 'baseFilename', '')).resolve() == log_file.resolve():
            file_handler = handler
            break

    if file_handler is None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    stream_handler = None
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
            stream_handler = handler
            break

    if stream_handler is None:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
