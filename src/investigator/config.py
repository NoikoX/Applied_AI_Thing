"""Configuration loading.

Secrets come from the environment (or a local .env file); everything else
comes from config/config.yaml. Both fail fast with a readable ConfigError.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


class ConfigError(RuntimeError):
    """Configuration is missing or invalid."""


class Secrets(BaseSettings):
    """API keys and credentials. Field names map to upper-case env vars."""

    model_config = SettingsConfigDict(extra="ignore")

    gemini_api_key: SecretStr
    openai_api_key: SecretStr
    qdrant_url: str
    qdrant_api_key: SecretStr
    admin_token: SecretStr


class ModelSpec(BaseModel):
    provider: Literal["gemini", "openai"]
    name: str
    temperature: float | None = 0.0  # None: let the model use its default
    reasoning_effort: str | None = None


class RetryConfig(BaseModel):
    max_attempts: int
    backoff_base_s: float
    backoff_max_s: float


class LLMConfig(BaseModel):
    planner: ModelSpec
    answer: ModelSpec
    grader: ModelSpec
    fallback: ModelSpec
    judge: ModelSpec
    timeout_s: float
    retry: RetryConfig
    cache_path: str
    log_path: str
    rate_limits: dict[str, tuple[int, int]]  # model -> (requests per minute, per day)


class EmbeddingConfig(BaseModel):
    provider: Literal["openai"]
    name: str
    comparison_name: str
    dimensions: int
    batch_size: int
    max_retries: int


ChunkingStrategy = Literal["paragraph", "sentence_window", "recursive"]


class IndexConfig(BaseModel):
    chunking_strategy: ChunkingStrategy
    near_duplicate_threshold: float


class CoverageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo in an eval override must fail loudly

    w_ce: float
    w_rrf: float
    w_cov: float
    redundancy_lambda: float
    max_chunks_per_doc: int
    covers_top_n: int
    min_score: float


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["dense", "sparse", "hybrid"]
    fusion: Literal["rrf", "weighted"]
    rrf_k: int
    dense_weight: float
    candidates_per_list: int
    rerank: bool
    rerank_top_n: int
    selection: Literal["topk", "coverage"]
    final_k: int
    coverage: CoverageConfig


class RAGConfig(BaseModel):
    min_relevance: float


class AgentConfig(BaseModel):
    max_hops: int
    max_queries_per_hop: int
    max_sources: int


class LocalModelsConfig(BaseModel):
    cache_dir: str
    threads: int | None  # None = all CPU cores (offline evaluation)
    sparse: str
    reranker: str


class SentenceWindowConfig(BaseModel):
    window: int
    stride: int


class RecursiveConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int


class ChunkingConfig(BaseModel):
    upload_strategy: ChunkingStrategy
    sentence_window: SentenceWindowConfig
    recursive: RecursiveConfig


class DatasetConfig(BaseModel):
    hf_name: str
    hf_config: str
    hf_revision: str
    split: str
    n_questions: int
    seed: int
    dev_fraction: float


class AppConfig(BaseModel):
    llm: LLMConfig
    embeddings: EmbeddingConfig
    index: IndexConfig
    retrieval: RetrievalConfig
    rag: RAGConfig
    agent: AgentConfig
    local_models: LocalModelsConfig
    chunking: ChunkingConfig
    dataset: DatasetConfig


def _describe(err: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in err.errors())


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return AppConfig.model_validate(raw)
    except ValidationError as err:
        raise ConfigError(f"Invalid config in {path}: {_describe(err)}") from err


def load_secrets(env_file: Path | None = DEFAULT_ENV_FILE) -> Secrets:
    """Read secrets from the environment, falling back to env_file if it exists."""
    try:
        return Secrets(_env_file=env_file)
    except ValidationError as err:
        missing = [str(e["loc"][0]).upper() for e in err.errors() if e["type"] == "missing"]
        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Copy .env.example to .env and fill them in."
            ) from err
        raise ConfigError(f"Invalid secrets: {_describe(err)}") from err
