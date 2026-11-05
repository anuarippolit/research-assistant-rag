from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    anthropic_api_key: str
    chat_model:  str = "claude-haiku-5-5"
    qdrant_url: str = "http://localhost:6333"
    collection: str = "chunks"

settings = Settings()