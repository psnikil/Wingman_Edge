import os
import logging
from typing import Optional, Any
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# LangChain Imports
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None
    logging.warning("langchain-ollama not installed.")

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None
    logging.warning("langchain-openai not installed.")

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None
    logging.warning("langchain-anthropic not installed.")

load_dotenv()

logger = logging.getLogger(__name__)

class LLMConfig(BaseSettings):
    """Configuration for LLM providers loaded from environment variables."""
    # Default Provider Configuration
    DEFAULT_LLM_PROVIDER: str = Field(default="ollama", env="DEFAULT_LLM_PROVIDER")

    # Ollama Settings
    OLLAMA_MODEL: str = Field(default="qwen3.5:2b", env="OLLAMA_MODEL")
    OLLAMA_TEMPERATURE: float = Field(default=0.0, env="OLLAMA_TEMPERATURE")
    OLLAMA_CONTEXT_WINDOW: int = Field(default=4096, env="OLLAMA_CONTEXT_WINDOW")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_TEMPERATURE: float = Field(default=0.0, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: Optional[int] = Field(default=None, env="OPENAI_MAX_TOKENS")

    # Anthropic Settings
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20240620", env="ANTHROPIC_MODEL")
    ANTHROPIC_TEMPERATURE: float = Field(default=0.0, env="ANTHROPIC_TEMPERATURE")
    ANTHROPIC_MAX_TOKENS: int = Field(default=4096, env="ANTHROPIC_MAX_TOKENS")

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

class LLMClient:
    """
    An abstraction for initializing LLMs from different providers.
    Supports Ollama, OpenAI, and Anthropic.
    """
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()

    def init_ollama(self, **kwargs) -> Any:
        """Initialize an Ollama model."""
        if ChatOllama is None:
            raise ImportError("langchain-ollama is not installed. Please install it to use Ollama.")
        # print(f"the kwargs are {kwargs}")
        params = {
            "model": kwargs.get("model", self.config.OLLAMA_MODEL),
            "temperature": kwargs.get("temperature", self.config.OLLAMA_TEMPERATURE),
            "num_ctx": kwargs.get("num_ctx", self.config.OLLAMA_CONTEXT_WINDOW),
            "base_url": kwargs.get("base_url", self.config.OLLAMA_BASE_URL),
    }

        params.update(kwargs)
        # print(f"Initializing Ollama model: {params['model']}")
        logger.info(f"Initializing Ollama model: {params['model']}")
        return ChatOllama(**params)

    def init_openai(self, **kwargs) -> Any:
        """Initialize an OpenAI model."""
        if ChatOpenAI is None:
            raise ImportError("langchain-openai is not installed. Please install it to use OpenAI.")
        
        params = {
            "model": kwargs.pop("model", self.config.OPENAI_MODEL),
            "openai_api_key": kwargs.pop("openai_api_key", self.config.OPENAI_API_KEY),
            "temperature": kwargs.pop("temperature", self.config.OPENAI_TEMPERATURE),
            "max_tokens": kwargs.pop("max_tokens", self.config.OPENAI_MAX_TOKENS),
            **kwargs
        }
        logger.info(f"Initializing OpenAI model: {params['model']}")
        return ChatOpenAI(**params)

    def init_anthropic(self, **kwargs) -> Any:
        """Initialize an Anthropic model."""
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed. Please install it to use Anthropic.")
        
        params = {
            "model": kwargs.pop("model", self.config.ANTHROPIC_MODEL),
            "anthropic_api_key": kwargs.pop("anthropic_api_key", self.config.ANTHROPIC_API_KEY),
            "temperature": kwargs.pop("temperature", self.config.ANTHROPIC_TEMPERATURE),
            "max_tokens": kwargs.pop("max_tokens", self.config.ANTHROPIC_MAX_TOKENS),
            **kwargs
        }
        logger.info(f"Initializing Anthropic model: {params['model']}")
        return ChatAnthropic(**params)

    def get_llm(self, provider: Optional[str] = None, **kwargs) -> Any:
        """
        Main function to initialize the LLM based on provider or default logic.
        
        Priority Logic:
        1. Explicitly requested 'provider' argument.
        2. OpenAI if OPENAI_API_KEY is present and not empty.
        3. Anthropic if ANTHROPIC_API_KEY is present and not empty.
        4. Ollama (default fallback).
        """
        if provider:
            provider = provider.lower()
            if provider == "ollama":
                return self.init_ollama(**kwargs)
            elif provider == "openai":
                return self.init_openai(**kwargs)
            elif provider == "anthropic":
                return self.init_anthropic(**kwargs)
            else:
                logger.warning(f"Unknown provider '{provider}', falling back to default logic.")

        # Default provider priority logic based on API keys
        if self.config.OPENAI_API_KEY and self.config.OPENAI_API_KEY.strip():
            try:
                return self.init_openai(**kwargs)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI despite API key: {e}")
        
        if self.config.ANTHROPIC_API_KEY and self.config.ANTHROPIC_API_KEY.strip():
            try:
                return self.init_anthropic(**kwargs)
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic despite API key: {e}")

        # Final fallback to Ollama
        return self.init_ollama(**kwargs)
