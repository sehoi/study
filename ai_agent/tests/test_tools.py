import pytest

from finance_agent.tools import CustomerToolkit


@pytest.fixture
def tools(toolkit: CustomerToolkit) -> dict:
    return {t.name: t for t in toolkit.as_tools()}


def test_toolkit_rejects_unknown_customer() -> None:
    with pytest.raises(KeyError):
        CustomerToolkit("C9999")


def test_get_accounts_only_returns_own_accounts(tools: dict) -> None:
    result = tools["get_accounts"].invoke({})
    assert "110-234-567890" in result
    assert "210-991-004512" not in result  # 다른 고객(C1002)의 계좌


def test_transactions_accept_masked_account_number(tools: dict) -> None:
    result = tools["get_transactions"].invoke({"account_no": "110-***-**7890", "limit": 2})
    assert "최근 거래 2건" in result
    assert "급여 입금" in result


def test_transactions_reject_other_customers_account(tools: dict) -> None:
    """LLM 이 타인 계좌번호를 만들어 넣어도 서버에서 막는다."""
    result = tools["get_transactions"].invoke({"account_no": "210-991-004512"})
    assert "본인 명의 계좌가 아니" in result
    assert "편의점 결제" not in result


def test_transaction_limit_is_clamped(tools: dict) -> None:
    result = tools["get_transactions"].invoke({"account_no": "110-234-567890", "limit": 999})
    assert result.count("\n- ") == 6  # 목 데이터 전체 건수


def test_report_card_lost_records_action(tools: dict, toolkit: CustomerToolkit) -> None:
    result = tools["report_card_lost"].invoke({"card_last4": "8842"})
    assert "접수번호 LOST-" in result
    assert len(toolkit.actions) == 1
    assert toolkit.actions[0].action == "카드 분실신고"
    assert toolkit.customer["cards"][0]["status"] == "분실신고"


def test_report_card_lost_is_idempotent(tools: dict, toolkit: CustomerToolkit) -> None:
    tools["report_card_lost"].invoke({"card_last4": "8842"})
    again = tools["report_card_lost"].invoke({"card_last4": "8842"})
    assert "이미 분실신고" in again
    assert len(toolkit.actions) == 1


def test_report_card_lost_unknown_card(tools: dict, toolkit: CustomerToolkit) -> None:
    assert "찾을 수 없습니다" in tools["report_card_lost"].invoke({"card_last4": "0000"})
    assert toolkit.actions == []


def test_limit_increase_requires_higher_limit(tools: dict) -> None:
    assert "크지 않아" in tools["request_limit_increase"].invoke(
        {"daily_limit": 1_000_000, "reason": "생활비"}
    )


def test_limit_increase_over_ten_million_needs_branch_visit(tools: dict) -> None:
    result = tools["request_limit_increase"].invoke(
        {"daily_limit": 20_000_000, "reason": "전세자금"}
    )
    assert "접수번호 LMT-" in result
    assert "영업점 방문" in result


def test_escalation_creates_ticket(tools: dict, toolkit: CustomerToolkit) -> None:
    result = tools["escalate_to_human"].invoke({"topic": "대출 상담", "summary": "주담대 문의"})
    assert "접수번호 CS-" in result
    assert toolkit.actions[0].detail == "주담대 문의"


def test_search_faq_returns_documents(tools: dict) -> None:
    assert "FAQ-005" in tools["search_faq"].invoke({"query": "예금자보호 한도"})
