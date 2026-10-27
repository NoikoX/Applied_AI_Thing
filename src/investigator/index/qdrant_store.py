"""Qdrant connection."""

from qdrant_client import QdrantClient

from investigator.config import Secrets


def connect(secrets: Secrets, timeout: int = 10) -> QdrantClient:
    return QdrantClient(
        url=secrets.qdrant_url,
        api_key=secrets.qdrant_api_key.get_secret_value(),
        timeout=timeout,
    )
