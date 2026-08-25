"""한결은행(가상) 고객센터 AI 상담 - Streamlit 데모.

실행:
    streamlit run app.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_core.messages import HumanMessage  # noqa: E402

from finance_agent.config import get_settings  # noqa: E402
from finance_agent.graph import build_graph, last_answer  # noqa: E402
from finance_agent.guardrails import mask_pii  # noqa: E402
from finance_agent.tools import CustomerToolkit, load_customers  # noqa: E402

st.set_page_config(page_title="한결은행 AI 상담", page_icon="🏦", layout="centered")

SETTINGS = get_settings()
CUSTOMERS = load_customers()

SUGGESTIONS = [
    "제 계좌 잔액이랑 최근 거래 알려주세요",
    "카드를 잃어버렸어요. 어떻게 해야 하나요?",
    "이체한도를 1일 800만원으로 올리고 싶어요",
    "예금자보호는 얼마까지 되나요?",
]


# ---------------------------------------------------------------------------- 세션
def reset_session(customer_id: str) -> None:
    """고객이 바뀌거나 상담을 새로 시작할 때 그래프와 이력을 새로 만든다."""
    toolkit = CustomerToolkit(customer_id, customers=CUSTOMERS)
    st.session_state.customer_id = customer_id
    st.session_state.toolkit = toolkit
    st.session_state.graph = build_graph(customer_id, settings=SETTINGS, toolkit=toolkit)
    st.session_state.thread_id = f"web-{uuid.uuid4().hex[:8]}"
    st.session_state.history = []


if "graph" not in st.session_state:
    reset_session(next(iter(CUSTOMERS)))


# ---------------------------------------------------------------------------- 사이드바
with st.sidebar:
    st.subheader("상담 세션")

    options = list(CUSTOMERS)
    selected = st.selectbox(
        "본인인증된 고객 (데모용 전환)",
        options,
        index=options.index(st.session_state.customer_id),
        format_func=lambda cid: f"{CUSTOMERS[cid]['name']} ({cid})",
    )
    if selected != st.session_state.customer_id:
        reset_session(selected)
        st.rerun()

    if st.button("상담 새로 시작", use_container_width=True):
        reset_session(st.session_state.customer_id)
        st.rerun()

    st.caption(f"모델: `{SETTINGS.claude_model}`")
    st.caption(f"스레드: `{st.session_state.thread_id}`")

    if not SETTINGS.has_credentials:
        st.error("`ANTHROPIC_API_KEY` 가 설정되지 않았습니다. `.env` 파일을 확인해 주세요.")

    st.divider()
    st.subheader("처리된 업무")
    actions = st.session_state.toolkit.actions
    if actions:
        for record in actions:
            st.markdown(f"**{record.ticket}**  \n{record.action}  \n:gray[{record.detail}]")
    else:
        st.caption("아직 접수된 업무가 없습니다.")

    st.divider()
    st.subheader("가드레일 로그")
    events = st.session_state.get("guard_events", [])
    if events:
        for event in events:
            kind = event.split(":", 1)[0]
            icon = {"차단": "🛑", "마스킹": "🔒", "출력경고": "⚠️"}.get(kind, "•")
            st.markdown(f"{icon} {event}")
    else:
        st.caption("탐지된 이벤트가 없습니다.")


# ---------------------------------------------------------------------------- 본문
customer = CUSTOMERS[st.session_state.customer_id]
st.title("🏦 한결은행 AI 상담")
st.caption(
    f"{customer['name']} 고객님({customer['grade']}) 본인인증 완료 · "
    "계좌·카드·이체 업무를 도와드립니다."
)

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        if turn.get("tools"):
            with st.expander(f"사용한 도구 {len(turn['tools'])}개"):
                for call in turn["tools"]:
                    st.markdown(f"`{call['name']}({call['args']})`")
                    st.code(call["result"], language="text")

if not st.session_state.history:
    st.markdown("**이렇게 물어보세요**")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        if cols[i % 2].button(suggestion, use_container_width=True, key=f"sug{i}"):
            st.session_state.pending = suggestion
            st.rerun()

prompt = st.chat_input("무엇을 도와드릴까요?") or st.session_state.pop("pending", None)


def stream_turn(text: str) -> tuple[str, list[dict[str, Any]]]:
    """그래프를 스트리밍 실행하고 (최종 답변, 도구 호출 내역) 을 돌려준다."""
    graph = st.session_state.graph
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    inputs = {"messages": [HumanMessage(content=text)], "guard_events": []}

    placeholder = st.empty()
    buffer = ""
    pending_calls: dict[str, dict[str, Any]] = {}
    tool_calls: list[dict[str, Any]] = []

    for mode, payload in graph.stream(inputs, config, stream_mode=["messages", "updates"]):
        if mode == "messages":
            chunk, meta = payload
            if meta.get("langgraph_node") == "agent" and chunk.text:
                buffer += chunk.text
                placeholder.markdown(buffer + " ▌")
        else:  # updates - 도구 호출/결과를 짝지어 기록한다
            for node, update in payload.items():
                for message in (update or {}).get("messages", []):
                    if node == "agent":
                        for call in getattr(message, "tool_calls", []) or []:
                            pending_calls[call["id"]] = {
                                "name": call["name"],
                                "args": call["args"],
                            }
                    elif node == "tools":
                        info = pending_calls.pop(message.tool_call_id, {"name": "?", "args": {}})
                        tool_calls.append({**info, "result": message.text})
                        placeholder.markdown(f"_{info['name']} 조회 중…_")

    # 스트리밍 텍스트 대신 출력 가드레일까지 적용된 최종 상태를 정본으로 사용한다.
    state = graph.get_state(config).values
    answer = last_answer(state) or buffer
    st.session_state.guard_events = state.get("guard_events", [])
    placeholder.markdown(answer)
    return answer, tool_calls


if prompt:
    # 화면에 남는 이력에도 원문 대신 마스킹된 문장을 보여준다.
    shown_prompt, _ = mask_pii(prompt)
    st.session_state.history.append({"role": "user", "content": shown_prompt})
    with st.chat_message("user"):
        st.markdown(shown_prompt)

    with st.chat_message("assistant"):
        try:
            answer, tool_calls = stream_turn(prompt)
        except Exception as exc:  # noqa: BLE001 - 데모에서는 원인을 화면에 보여준다
            answer, tool_calls = f"⚠️ 상담 처리 중 오류가 발생했습니다: `{exc}`", []
            st.markdown(answer)
        else:
            if tool_calls:
                with st.expander(f"사용한 도구 {len(tool_calls)}개"):
                    for call in tool_calls:
                        st.markdown(f"`{call['name']}({call['args']})`")
                        st.code(call["result"], language="text")

    st.session_state.history.append({"role": "assistant", "content": answer, "tools": tool_calls})
    st.rerun()
