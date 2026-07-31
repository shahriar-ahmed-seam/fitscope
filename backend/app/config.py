"""Runtime configuration for the FitScope API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    app_name: str = "FitScope API"
    app_version: str = "1.0.0"
    public_base_url: str = "http://localhost:3000"

    # --- LLM (DeepSeek) ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 120.0
    llm_max_output_tokens: int = 3000

    # --- Embeddings + reranking (Voyage AI) ---
    voyage_api_key: str = ""
    voyage_base_url: str = "https://api.voyageai.com/v1"
    voyage_embed_model: str = "voyage-3.5-lite"
    voyage_rerank_model: str = "rerank-2.5-lite"
    voyage_embed_dim: int = 1024
    # Voyage applies 3 RPM / 10K TPM until a payment method is added, so calls are
    # shaped by a token bucket and the per-requirement reranker is opt-in.
    voyage_requests_per_minute: int = 3
    voyage_max_wait_seconds: float = 6.0
    voyage_rerank_enabled: bool = False

    # --- Storage ---
    database_url: str = ""

    # --- Scoring knobs (documented in README, tuned with eval/run_eval.py) ---
    judge_enabled: bool = True
    judge_candidates_per_requirement: int = 6
    # Thresholds used when coverage falls back to a similarity score instead of
    # the LLM judge (lexical or reranker relevance, both 0-1).
    covered_threshold: float = 0.55
    partial_threshold: float = 0.32
    weight_must_have: float = 3.0
    weight_responsibility: float = 1.5
    weight_nice_to_have: float = 1.0
    semantic_weight: float = 0.65
    ats_weight: float = 0.35
    retrieval_top_k: int = 8

    # --- Abuse / cost control ---
    rate_limit_per_day: int = 25
    api_keys: str = ""  # comma separated keys that bypass the IP rate limit
    max_upload_bytes: int = 2_500_000
    max_jd_chars: int = 30_000

    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        raw = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        return raw or ["http://localhost:3000"]

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def weights(self) -> dict[str, float]:
        return {
            "must_have": self.weight_must_have,
            "responsibility": self.weight_responsibility,
            "nice_to_have": self.weight_nice_to_have,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
