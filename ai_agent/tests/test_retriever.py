import pytest

from finance_agent.retriever import get_retriever, tokenize


def test_tokenize_adds_korean_bigrams() -> None:
    tokens = tokenize("이체한도")
    assert "이체한도" in tokens
    assert "이체" in tokens and "체한" in tokens


def test_tokenize_drops_single_characters() -> None:
    """한 글자 토큰은 노이즈라 색인하지 않는다."""
    assert tokenize("가 a 1 은행") == ["은행", "은행"]


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("이체 한도 올리고 싶어요", "FAQ-001"),
        ("카드 잃어버렸어요", "FAQ-002"),
        ("보이스피싱 당한 것 같아요", "FAQ-003"),
        ("예금자보호 한도", "FAQ-005"),
        ("해외로 송금하려면", "FAQ-007"),
        ("ATM 몇 시까지 쓸 수 있나요", "FAQ-010"),
    ],
)
def test_top_hit(query: str, expected_id: str) -> None:
    hits = get_retriever().search(query, top_k=1)
    assert hits and hits[0][0].id == expected_id


def test_unrelated_query_returns_nothing_or_low_score() -> None:
    hits = get_retriever().search("!!!", top_k=3)
    assert hits == []
