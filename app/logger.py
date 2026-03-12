import logging

from app.config import LOGS_DIR, LOG_FILE


LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("workspace_automation")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger