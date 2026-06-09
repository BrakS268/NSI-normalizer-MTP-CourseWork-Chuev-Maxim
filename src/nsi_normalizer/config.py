from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://nsi:nsi@localhost:5432/nsi_db"
    redis_url: str = "redis://localhost:6379/0"
    api_key_hash: str = "changeme"
    debug: bool = False
    use_embeddings: bool = False
    anthropic_api_key: str = ""
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 256
    dedup_confidence_threshold: float = 0.65
    llm_uncertainty_low: float = 0.35
    llm_uncertainty_high: float = 0.65


settings = Settings()
