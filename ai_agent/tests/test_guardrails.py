import pytest

from finance_agent.guardrails import (
    apply_output_guard,
    mask_pii,
    scan_output,
    screen_input,
)


@pytest.mark.parametrize(
    ("raw", "expected_label", "must_not_contain"),
    [
        ("주민번호 900101-1234567 입니다", "주민등록번호", "1234567"),
        ("카드 1234-5678-9012-3456 확인", "카드번호", "1234-5678-9012"),
        ("제 번호는 010-1234-5678", "전화번호", "1234-5678"),
        ("계좌 110-234-567890 조회", "계좌번호", "110-234-567890"),
        ("메일 hong@example.com 로 보내주세요", "이메일", "hong@example.com"),
    ],
)
def test_mask_pii(raw: str, expected_label: str, must_not_contain: str) -> None:
    masked, findings = mask_pii(raw)
    assert expected_label in findings
    assert must_not_contain not in masked


def test_mask_account_keeps_last_four_digits() -> None:
    """도구가 뒤 4자리로 본인 계좌를 식별할 수 있어야 한다."""
    masked, _ = mask_pii("110-234-567890")
    assert masked.endswith("7890")


def test_phone_is_not_mistaken_for_account() -> None:
    _, findings = mask_pii("010-1234-5678")
    assert findings == ["전화번호"]


@pytest.mark.parametrize(
    ("raw", "category"),
    [
        ("비밀번호는 483921 이에요", "인증정보_노출"),
        ("OTP 번호 552134 입력했어요", "인증정보_노출"),
        ("대포통장 하나 구할 수 있나요", "불법금융"),
        ("어떤 주식 살까요?", "투자권유_요구"),
        ("원금 보장되는 상품 추천해줘", "투자권유_요구"),
    ],
)
def test_blocked_inputs(raw: str, category: str) -> None:
    result = screen_input(raw)
    assert result.blocked
    assert result.category == category
    assert result.response


def test_blocked_input_is_also_masked() -> None:
    result = screen_input("비밀번호는 483921 이에요")
    assert "483921" not in result.text


@pytest.mark.parametrize(
    "raw",
    ["이체한도 올리고 싶어요", "카드 분실신고 하고 싶습니다", "예금자보호 한도가 얼마인가요"],
)
def test_normal_inputs_pass(raw: str) -> None:
    assert not screen_input(raw).blocked


def test_output_guard_appends_disclaimer() -> None:
    text, violations = apply_output_guard("이 상품은 원금이 보장됩니다.")
    assert violations == ["원금보장_표현"]
    assert "원금 손실이 발생할 수 있고" in text


def test_output_guard_is_noop_for_safe_text() -> None:
    text, violations = apply_output_guard("잔액은 3,250,400원입니다.")
    assert violations == []
    assert text == "잔액은 3,250,400원입니다."
    assert scan_output(text) == []
