"""
Deterministic mock response adapter with outbound identifier pattern checks.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Split Learning Privacy Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} Mock]: No model inference or clinical verification performed. Received query: '{prompt[:60]}...'."


class LLMFactory:
    """Creates the deterministic mock adapter; external providers are not implemented."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Split Learning Privacy Agent"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError(
            f"Model provider '{provider}' is not implemented. "
            "Select 'mock'; no external LLM integrations are installed."
        )
