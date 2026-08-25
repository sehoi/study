from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from finance_agent.config import Settings
from finance_agent.graph import build_graph, last_answer
from finance_agent.tools import CustomerToolkit

from .conftest import ScriptedModel


def _run(graph: Any, text: str, thread: str = "t1") -> dict[str, Any]:
    return graph.invoke(
        {"messages": [HumanMessage(content=text)], "guard_events": []},
        config={"configurable": {"thread_id": thread}},
    )


def test_blocked_input_never_reaches_the_model(
    settings: Settings, toolkit: CustomerToolkit
) -> None:
    model = ScriptedModel([])  # 호출되면 AssertionError 가 난다
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    state = _run(graph, "어떤 주식 살까요?")

    assert model.calls == []
    assert "투자 권유" in last_answer(state)
    assert "차단:투자권유_요구" in state["guard_events"]


def test_pii_is_masked_before_reaching_the_model(
    settings: Settings, toolkit: CustomerToolkit
) -> None:
    model = ScriptedModel([AIMessage(content="확인해 드리겠습니다.")])
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    state = _run(graph, "제 주민번호 900101-1234567 로 조회해주세요")

    sent = "\n".join(m.text for m in model.calls[0])
    assert "1234567" not in sent
    assert "마스킹:주민등록번호" in state["guard_events"]
    # 대화 이력에도 원문이 남지 않아야 한다.
    assert all("900101-1234567" not in m.text for m in state["messages"])


def test_tool_call_round_trip(settings: Settings, toolkit: CustomerToolkit) -> None:
    model = ScriptedModel(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "get_accounts", "args": {}, "id": "call-1"}],
            ),
            AIMessage(content="입출금통장 잔액은 3,250,400원입니다."),
        ]
    )
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    state = _run(graph, "잔액 알려주세요")

    tool_output = state["messages"][-2].text
    assert "3,250,400원" in tool_output
    assert last_answer(state) == "입출금통장 잔액은 3,250,400원입니다."


def test_output_guard_appends_disclaimer(settings: Settings, toolkit: CustomerToolkit) -> None:
    model = ScriptedModel([AIMessage(content="이 상품은 원금이 보장됩니다.")])
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    state = _run(graph, "이 상품 안전한가요?")

    assert "원금 손실이 발생할 수 있고" in last_answer(state)
    assert "출력경고:원금보장_표현" in state["guard_events"]


def test_tool_loop_is_capped(settings: Settings, toolkit: CustomerToolkit) -> None:
    """상한(3회)에 도달하면 도구 없이 마무리 답변을 만든다."""
    looping = [
        AIMessage(content="", tool_calls=[{"name": "get_cards", "args": {}, "id": f"c{i}"}])
        for i in range(settings.max_tool_iterations)
    ]
    model = ScriptedModel([*looping, AIMessage(content="상담원 연결을 도와드릴까요?")])
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    state = _run(graph, "카드 상태 알려주세요")

    assert last_answer(state) == "상담원 연결을 도와드릴까요?"
    assert model.bound_tools  # 도구는 바인딩되어 있었지만
    # 마지막 호출에는 상한 안내 시스템 메시지가 붙는다.
    assert "상담원 연결" in model.calls[-1][-1].text


def test_conversation_history_persists_across_turns(
    settings: Settings, toolkit: CustomerToolkit
) -> None:
    model = ScriptedModel([AIMessage(content="첫 번째"), AIMessage(content="두 번째")])
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    _run(graph, "안녕하세요", thread="same")
    _run(graph, "카드 알려주세요", thread="same")

    second_call = model.calls[1]
    assert any(m.text == "안녕하세요" for m in second_call)
    assert any(m.text == "첫 번째" for m in second_call)


def test_threads_are_isolated(settings: Settings, toolkit: CustomerToolkit) -> None:
    model = ScriptedModel([AIMessage(content="A"), AIMessage(content="B")])
    graph = build_graph("C1001", settings=settings, toolkit=toolkit, llm=model)

    _run(graph, "고객 A 문의", thread="a")
    _run(graph, "고객 B 문의", thread="b")

    assert all("고객 A 문의" != m.text for m in model.calls[1])
