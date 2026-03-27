from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Supply Chain Agent"
    API_V1_STR: str = "/api"
    
    # Auth
    SECRET_KEY: str = "your-secret-key-should-be-complex-and-stored-in-env" # 在生产环境中请修改
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1天

    # Database
    DATABASE_URL: str = "postgresql://postgres:1234@localhost:5432/supply_chain_agent"

    # LLM (未来扩展)
    LLM_PROVIDER: str = "openai" # openai, deepseek, ollama
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    # Admin Init
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "allow" # 允许额外的环境变量

settings = Settings()
