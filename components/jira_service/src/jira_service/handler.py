"""Adds mangum support for lambda deployment."""

import json
import logging
from typing import Any

from mangum import Mangum

from jira_service.main import app  # type: ignore[import-not-found]

logger = logging.getLogger()
logger.setLevel(logging.INFO)

mangum_handler = Mangum(app, lifespan="off")

def handler(event : dict[str, Any], context : Any) -> dict[str, Any]: # noqa: ANN401
    """Handle HTTP messages sent to lambda."""
    logger.info("in handler.py")
    logger.info("Incoming Event:")
    logger.info(json.dumps(event, indent = 2))

    return mangum_handler(event, context)
