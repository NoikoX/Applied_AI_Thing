"""On-disk cache of LLM responses (SQLite).

Temperature 0 plus caching makes evaluation repeatable and free to re-run:
the same request (provider, model, messages, parameters, output schema, tools)
always returns the stored answer.
"""

import hashlib
import json
import sqlite3
from pathlib import Path


def cache_key(request: dict) -> str:
    """Stable hash of everything that can change the answer."""
    blob = json.dumps(request, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI may call from different worker threads.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT)")

    def get(self, key: str) -> dict | None:
        row = self._db.execute("SELECT value FROM responses WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        self._db.execute("INSERT OR REPLACE INTO responses VALUES (?, ?)", (key, json.dumps(value)))
        self._db.commit()
