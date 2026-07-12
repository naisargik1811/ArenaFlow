import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str | None
    nvidia_model: str
    app_title: str = "ArenaFlow"
    app_subtitle: str = "GenAI Operations for FIFA World Cup 2026"

def load_settings() -> Settings:
    return Settings(
        nvidia_api_key=os.getenv("NVIDIA_API_KEY") or None,
        nvidia_model=os.getenv("NVIDIA_MODEL") or "meta/llama-3.1-8b-instruct",
    )
