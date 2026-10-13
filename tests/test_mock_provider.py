"""Ensure simulated providers never masquerade as real model inference."""
import pytest
from agents.llm_factory import LLMFactory


def test_mock_is_labelled_not_verified():
    result = LLMFactory.create("mock").invoke("status")
    assert "No model inference" in result
    assert "Mock" in result


@pytest.mark.parametrize("provider", ["openai", "claude", "ollama", "unknown"])
def test_unimplemented_providers_fail_loudly(provider):
    with pytest.raises(ValueError, match="not implemented"):
        LLMFactory.create(provider)
