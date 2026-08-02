"""
utils/logger.py
----------------
One shared logger configuration so every module logs consistently
instead of sprinkling print() statements around the codebase.
"""

import logging
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED

    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)-7s %(name)-28s | %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stdout,
        )
        _CONFIGURED = True

    return logging.getLogger(name)
