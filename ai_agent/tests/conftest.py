"""테스트 공용 픽스처.

실제 Claude API 를 호출하지 않고 그래프 로직만 검증하기 위해 스크립트 기반
가짜 모델을 주입한다(`build_graph(..., llm=...)`).
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage

from finance_agent.config import Settings
from finance_agent.tools import CustomerToolkit


class ScriptedModel:
    """미리 준비한 AIMessage 를 순서대로 돌려주는 가짜 채팅 모델."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = list(responses)
        self.calls: list[list[Any]] = []
        self.bound_tools: list[Any] = []

    def bind_tools(self, tools: list[Any]) -> ScriptedModel:
        self.bound_tools = tools
        return self

    def invoke(self, messages: list[Any], **_: Any) -> AIMessage:
        self.calls.append(list(messages))
        if not self._responses:
            raise AssertionError("가짜 모델에 준비된 응답보다 많은 호출이 발생했습니다.")
        return self._responses.pop(0)


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="test-key", max_tool_iterations=3)


@pytest.fixture
def toolkit() -> CustomerToolkit:
    return CustomerToolkit("C1001")
