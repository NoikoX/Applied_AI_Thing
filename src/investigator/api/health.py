"""Health checks and memory readings."""

import logging

import psutil
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)
MB = 1024 * 1024


def rss_mb() -> float:
    """Current resident memory of this process."""
    return psutil.Process().memory_info().rss / MB


def peak_rss_mb() -> float:
    """Highest resident memory since the process started."""
    try:
        import resource
    except ImportError:  # Windows has no `resource` module
        return psutil.Process().memory_info().peak_wset / MB
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux reports KB


def qdrant_is_reachable(client: QdrantClient) -> bool:
    try:
        client.get_collections()
    except Exception:
        logger.exception("Qdrant health check failed")
        return False
    return True
