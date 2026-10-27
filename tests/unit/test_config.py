import pytest

from investigator.config import (
    PROJECT_ROOT,
    ConfigError,
    Secrets,
    load_config,
    load_secrets,
)

SECRET_VARS = [name.upper() for name in Secrets.model_fields]


@pytest.fixture
def clean_env(monkeypatch):
    for name in SECRET_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_project_config_loads():
    cfg = load_config()
    assert cfg.llm.fallback.provider == "openai"
    assert cfg.embeddings.name
    assert cfg.dataset.seed == 42
    assert cfg.dataset.n_questions == 5000


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_invalid_config_names_the_bad_field(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("llm: {}\nembeddings: {}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="dataset"):
        load_config(path)


def test_unknown_provider_rejected(tmp_path):
    text = (PROJECT_ROOT / "config" / "config.yaml").read_text(encoding="utf-8")
    path = tmp_path / "config.yaml"
    path.write_text(text.replace("provider: gemini", "provider: mystery", 1), encoding="utf-8")
    with pytest.raises(ConfigError, match="provider"):
        load_config(path)


def test_secrets_read_from_environment(clean_env):
    for name in SECRET_VARS:
        clean_env.setenv(name, f"value-{name}")
    secrets = load_secrets(env_file=None)
    assert secrets.openai_api_key.get_secret_value() == "value-OPENAI_API_KEY"
    assert "value-OPENAI_API_KEY" not in repr(secrets)


def test_missing_secret_gives_clear_error(clean_env):
    for name in SECRET_VARS:
        if name != "GEMINI_API_KEY":
            clean_env.setenv(name, "x")
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_secrets(env_file=None)


def test_env_example_lists_every_secret():
    lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    keys = {line.split("=", 1)[0] for line in lines if "=" in line and not line.startswith("#")}
    assert keys == set(SECRET_VARS)
