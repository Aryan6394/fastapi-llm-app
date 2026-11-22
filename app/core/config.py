from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI LLM Microservice"
    API_V1_STR: str = "/api/v1"
    
    # Security
    API_KEY: str
    
    # LLM Settings
    GEMINI_API_KEY: str 
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()