import logging


def get_logger(level: str = "INFO"):
    logger = logging.getLogger("dtm2cat")
    logger.setLevel(getattr(logging, level))
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
