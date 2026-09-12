"""LLM clients for P2: Groq = classification, Gemini = generation."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Literal

from src.config import AppConfig, LlmEndpointConfig

Role = Literal["classify", "generate"]

_last_call_lock = threading.Lock()
_last_call_at: dict[str, float] = {"classify": 0.0, "generate": 0.0}


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _endpoint(cfg: AppConfig, role: Role) -> LlmEndpointConfig:
    if role == "classify":
        return cfg.langchain.classify
    return cfg.langchain.generate


def llm_available(cfg: AppConfig, role: Role | None = None) -> bool:
    load_dotenv_if_present()
    if role is None:
        return bool(os.getenv("GROQ_API_KEY")) and bool(
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
    endpoint = _endpoint(cfg, role)
    provider = (endpoint.provider or "").lower()
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    if provider in {"gemini", "google"}:
        return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    return False


def _throttle(endpoint: LlmEndpointConfig, role: Role) -> None:
    """Space calls to stay under the endpoint's requests-per-minute."""
    rpm = max(int(endpoint.requests_per_minute or 30), 1)
    min_interval = 60.0 / rpm
    with _last_call_lock:
        now = time.monotonic()
        wait = min_interval - (now - _last_call_at[role])
        if wait > 0:
            time.sleep(wait)
        _last_call_at[role] = time.monotonic()


class _ThrottledChatModel:
    """Thin wrapper that spaces invoke() calls per role."""

    def __init__(self, model: Any, endpoint: LlmEndpointConfig, role: Role) -> None:
        self._model = model
        self._endpoint = endpoint
        self._role = role
        self.provider = endpoint.provider
        self.model_name = endpoint.model

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        _throttle(self._endpoint, self._role)
        return self._model.invoke(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)


def _build_raw_model(endpoint: LlmEndpointConfig) -> Any | None:
    provider = (endpoint.provider or "").lower()
    model_name = endpoint.model
    temperature = float(endpoint.temperature or 0)

    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            return None
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise ImportError(
                "langchain-groq is required for Groq classification. "
                "pip install langchain-groq"
            ) from exc
        return ChatGroq(model=model_name, temperature=temperature)

    if provider in {"gemini", "google"}:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ImportError(
                "langchain-google-genai is required for Gemini generation. "
                "pip install langchain-google-genai"
            ) from exc
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
        )

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return None
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, temperature=temperature)

    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, temperature=temperature)

    return None


def get_chat_model(cfg: AppConfig, role: Role = "generate") -> Any | None:
    """
    Return a LangChain chat model for the given role.

    - classify → Groq (`openai/gpt-oss-120b`) for review theme labeling
    - generate → Gemini for theme copy, quotes, actions, compose
    """
    load_dotenv_if_present()
    endpoint = _endpoint(cfg, role)
    raw = _build_raw_model(endpoint)
    if raw is None:
        return None
    return _ThrottledChatModel(raw, endpoint, role)


def get_classify_model(cfg: AppConfig) -> Any | None:
    """Groq (or configured classify provider) for review classification."""
    return get_chat_model(cfg, role="classify")


def get_generate_model(cfg: AppConfig) -> Any | None:
    """Gemini (or configured generate provider) for pulse generation."""
    return get_chat_model(cfg, role="generate")
