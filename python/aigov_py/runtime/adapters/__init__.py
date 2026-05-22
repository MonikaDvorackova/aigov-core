"""Framework adapters for embedding GovAI runtime governance (lazy imports only)."""

from aigov_py.runtime.adapters import fastapi
from aigov_py.runtime.adapters import langchain
from aigov_py.runtime.adapters import openai_gateway

__all__ = ["fastapi", "langchain", "openai_gateway"]
