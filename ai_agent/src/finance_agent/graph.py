"""LangGraph 에이전트 그래프.

    START ─→ guard ─┬─(차단)──────────────────────────────→ END
                    └─→ agent ─┬─(도구 호출 있음)→ tools ─┘(다시 agent)
                               └─(최종 답변)───────────────→ END

`guard` 는 LLM 을 거치지 않는 결정적 방어선이고, `agent` 는 도구를 든 LLM,
`tools` 는 LangGraph 기본 제공 ToolNode 다. 대화 이력은 체크포인터에 `thread_id`
단위로 저장되므로 Streamlit 세션은 메시지 배열을 직접 관리하지 않아도 된다.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from finance_agent.config import Settings, get_settings
from finance_agent.guardrails import apply_output_guard, screen_input
from finance_agent.prompts import TOOL_LIMIT_MESSAGE, build_system_prompt
from finance_agent.tools import CustomerToolkit


class AgentState(TypedDict):
    """그래프가 주고받는 상태."""

    messages: Annotated[list[AnyMessage], add_messages]
    # 가드레일이 탐지한 항목(마스킹된 PII 종류, 차단 사유). 감사·모니터링용으로 누적한다.
    guard_events: Annotated[list[str], operator.add]


def build_llm(settings: Settings) -> ChatAnthropic:
    """Claude 클라이언트 생성.

    주의: Claude Opus 5 는 temperature / top_p 등 샘플링 파라미터를 받으면 400 을 반환한다.
    또한 thinking 이 기본으로 켜져 있으므로 별도 설정을 넘기지 않는다.
    """
    return ChatAnthropic(
        model=settings.claude_model,
        max_tokens=settings.max_tokens,
        api_key=settings.anthropic_api_key,
    )


def _tool_rounds(messages: list[AnyMessage]) -> int:
    return sum(1 for m in messages if isinstance(m, AIMessage) and m.tool_calls)


def build_graph(
    customer_id: str,
    *,
    settings: Settings | None = None,
    toolkit: CustomerToolkit | None = None,
    llm: Any | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    """고객 한 명에게 바인딩된 그래프를 컴파일한다.

    Args:
        customer_id: 본인인증이 끝난 고객 ID. 도구는 이 값에 고정된다.
        settings: 설정. 생략하면 환경변수에서 읽는다.
        toolkit: 도구 모음. 생략하면 새로 만든다(테스트에서 주입 가능).
        llm: 채팅 모델. 생략하면 ChatAnthropic 을 만든다(테스트에서 가짜 모델 주입 가능).
        checkpointer: 대화 저장소. 생략하면 인메모리.
    """
    settings = settings or get_settings()
    toolkit = toolkit or CustomerToolkit(customer_id)
    tools = toolkit.as_tools()

    model = llm if llm is not None else build_llm(settings)
    model_with_tools = model.bind_tools(tools)

    system_prompt = build_system_prompt(
        bank_name=settings.bank_name,
        agent_name=settings.agent_name,
        customer_name=toolkit.customer["name"],
        customer_grade=toolkit.customer["grade"],
    )

    # ------------------------------------------------------------------ 노드
    def guard(state: AgentState) -> dict[str, Any]:
        """LLM 호출 전에 민감정보를 가리고 금지 요청을 차단한다."""
        last = state["messages"][-1]
        if not isinstance(last, HumanMessage):
            return {}

        result = screen_input(last.text)
        updates: dict[str, Any] = {}
        events = [f"마스킹:{name}" for name in result.findings]

        messages: list[AnyMessage] = []
        if result.text != last.text:
            # 같은 id 로 덮어써서 원문이 이후 턴에 남지 않도록 한다.
            messages.append(HumanMessage(content=result.text, id=last.id))
        if result.blocked:
            events.append(f"차단:{result.category}")
            messages.append(AIMessage(content=result.response or ""))

        if messages:
            updates["messages"] = messages
        if events:
            updates["guard_events"] = events
        return updates

    def agent(state: AgentState) -> dict[str, Any]:
        """도구를 든 LLM 호출. 도구 라운드 상한을 넘으면 도구 없이 마무리한다."""
        rounds = _tool_rounds(state["messages"])
        prompt: list[AnyMessage] = [SystemMessage(content=system_prompt), *state["messages"]]

        if rounds >= settings.max_tool_iterations:
            prompt.append(SystemMessage(content=TOOL_LIMIT_MESSAGE))
            response = model.invoke(prompt)
        else:
            response = model_with_tools.invoke(prompt)

        # 최종 답변에만 출력 가드레일을 적용한다(도구 호출 턴은 사용자에게 보이지 않음).
        if not getattr(response, "tool_calls", None):
            guarded, violations = apply_output_guard(response.text)
            if violations:
                return {
                    "messages": [AIMessage(content=guarded, id=response.id)],
                    "guard_events": [f"출력경고:{v}" for v in violations],
                }
        return {"messages": [response]}

    # ------------------------------------------------------------------ 분기
    def route_after_guard(state: AgentState) -> str:
        return END if isinstance(state["messages"][-1], AIMessage) else "agent"

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    builder = StateGraph(AgentState)
    builder.add_node("guard", guard)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "guard")
    builder.add_conditional_edges("guard", route_after_guard, {"agent": "agent", END: END})
    builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def last_answer(state: dict[str, Any]) -> str:
    """그래프 결과 상태에서 사용자에게 보여줄 마지막 답변을 꺼낸다."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return message.text
    return ""
