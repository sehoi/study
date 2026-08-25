"""금융권 챗봇에 필요한 최소한의 가드레일.

세 가지 역할을 한다.

1. **PII 마스킹** - 주민등록번호·카드번호·계좌번호 등을 LLM 에 보내기 *전에* 가린다.
   (모델에 원문이 전달되지 않으므로 로그·프롬프트 캐시에도 남지 않는다.)
2. **입력 차단** - 비밀번호/OTP 노출, 불법 금융 요청, 투자 권유 요구를 룰 기반으로 차단한다.
   LLM 판단에만 의존하지 않는 결정적(deterministic) 방어선이다.
3. **출력 검사** - "원금 보장" 같은 금융소비자보호법상 위험 표현을 탐지한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------------------
# PII 마스킹
# --------------------------------------------------------------------------------------

_RRN = re.compile(r"\b(\d{6})[-\s]?([1-4]\d{6})\b")
_CARD = re.compile(r"\b(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})\b")
_PHONE = re.compile(r"\b(01[016-9])[-\s]?(\d{3,4})[-\s]?(\d{4})\b")
_ACCOUNT = re.compile(r"\b(\d{2,3})-(\d{2,6})-(\d{2,7})\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_SECRET = re.compile(
    r"((?:비밀번호|비번|패스워드|password|OTP|오티피|보안카드|CVC|cvc)\s*(?:는|은|:|=)?\s*)(\d{3,10})",
    re.IGNORECASE,
)


def _mask_rrn(m: re.Match[str]) -> str:
    return f"{m.group(1)}-*******"


def _mask_card(m: re.Match[str]) -> str:
    return f"****-****-****-{m.group(4)}"


def _mask_phone(m: re.Match[str]) -> str:
    return f"{m.group(1)}-****-{m.group(3)}"


def _mask_account(m: re.Match[str]) -> str:
    """가운데 자리는 전부 가리고 뒤 4자리만 남긴다.

    뒤 4자리를 남기는 이유는 조회 도구가 마스킹된 계좌번호로도 본인 계좌를
    식별할 수 있게 하기 위함이다(`banking._resolve_account` 참고).
    """
    tail = m.group(3)
    return f"{m.group(1)}-***-{'*' * max(len(tail) - 4, 0)}{tail[-4:]}"


def _mask_email(m: re.Match[str]) -> str:
    local, _, domain = m.group(0).partition("@")
    return f"{local[:2]}***@{domain}"


def _mask_secret(m: re.Match[str]) -> str:
    return f"{m.group(1)}{'*' * len(m.group(2))}"


# 순서가 중요하다. 전화번호(010-1234-5678)는 계좌번호 패턴에도 걸리므로 먼저 처리한다.
_MASKERS: list[tuple[str, re.Pattern[str], object]] = [
    ("주민등록번호", _RRN, _mask_rrn),
    ("카드번호", _CARD, _mask_card),
    ("전화번호", _PHONE, _mask_phone),
    ("계좌번호", _ACCOUNT, _mask_account),
    ("이메일", _EMAIL, _mask_email),
    ("인증정보", _SECRET, _mask_secret),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """민감정보를 마스킹한 문자열과 탐지된 항목 이름 목록을 돌려준다."""
    findings: list[str] = []
    masked = text
    for label, pattern, repl in _MASKERS:
        masked, n = pattern.subn(repl, masked)  # type: ignore[arg-type]
        if n:
            findings.append(label)
    return masked, findings


# --------------------------------------------------------------------------------------
# 입력 차단 룰
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockRule:
    category: str
    patterns: tuple[str, ...]
    response: str


BLOCK_RULES: tuple[BlockRule, ...] = (
    BlockRule(
        category="인증정보_노출",
        patterns=(
            r"(비밀번호|비번|패스워드|password)\s*(는|은|:|=)?\s*\d{3,}",
            r"(OTP|오티피|보안카드)\s*(번호)?\s*(는|은|:|=)?\s*\d{3,}",
        ),
        response=(
            "채팅창에 비밀번호나 OTP·보안카드 번호를 입력하지 말아 주세요. "
            "은행 직원과 상담 시스템은 어떤 경우에도 이 정보를 요구하지 않습니다.\n\n"
            "입력하신 내용은 저장하지 않고 즉시 폐기했습니다. "
            "해당 번호가 이미 노출되었을 수 있으니 앱의 보안센터에서 비밀번호를 변경하시고, "
            "필요하시면 상담원 연결을 도와드리겠습니다."
        ),
    ),
    BlockRule(
        category="불법금융",
        patterns=(
            r"(대포통장|대포폰|명의\s*대여|명의\s*도용|자금\s*세탁|작업\s*대출|통장\s*(삽니다|팝니다|대여))",
        ),
        response=(
            "요청하신 내용은 관련 법령상 도와드릴 수 없는 사항입니다.\n\n"
            "통장·카드의 양도나 대여는 전자금융거래법 위반으로 처벌 대상이며, "
            "피해가 우려되는 상황이라면 금융감독원(1332) 또는 경찰(112)로 신고해 주세요."
        ),
    ),
    BlockRule(
        category="투자권유_요구",
        patterns=(
            r"(어떤|무슨|어느)\s*(주식|종목|코인|펀드).{0,10}(사|살까|살까요|추천|매수)",
            r"(수익|원금).{0,6}(보장|보증)",
            r"(무조건|확실히|반드시).{0,6}(오르|수익|버는)",
            r"(투자|매수|매도)\s*(추천|권유)\s*(해|좀|부탁)",
        ),
        response=(
            "죄송합니다. 저는 특정 상품의 투자 권유나 수익률 예측은 안내해 드릴 수 없습니다. "
            "금융소비자보호법에 따라 투자 권유는 자격을 갖춘 상담 인력을 통해서만 가능합니다.\n\n"
            "대신 예·적금 금리, 상품 조건, 예금자보호 범위 같은 사실 정보는 안내해 드릴 수 있어요. "
            "투자 상담이 필요하시면 상담원 연결을 도와드릴까요?"
        ),
    ),
)

_COMPILED_RULES = tuple(
    (rule, tuple(re.compile(p, re.IGNORECASE) for p in rule.patterns)) for rule in BLOCK_RULES
)


@dataclass
class ScreenResult:
    """입력 스크리닝 결과."""

    text: str
    blocked: bool = False
    category: str | None = None
    response: str | None = None
    findings: list[str] = field(default_factory=list)


def screen_input(text: str) -> ScreenResult:
    """사용자 입력을 마스킹하고 차단 여부를 판단한다.

    차단 판단은 *원문* 기준으로 먼저 수행한다. 마스킹된 문자열로 검사하면
    "비밀번호는 ****" 형태가 되어 룰이 걸리지 않기 때문이다.
    """
    for rule, patterns in _COMPILED_RULES:
        if any(p.search(text) for p in patterns):
            masked, findings = mask_pii(text)
            return ScreenResult(
                text=masked,
                blocked=True,
                category=rule.category,
                response=rule.response,
                findings=findings,
            )

    masked, findings = mask_pii(text)
    return ScreenResult(text=masked, findings=findings)


# --------------------------------------------------------------------------------------
# 출력 검사
# --------------------------------------------------------------------------------------

_OUTPUT_VIOLATIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("원금보장_표현", re.compile(r"원금\s*(이|은)?\s*(보장|보증)")),
    ("수익확정_표현", re.compile(r"(확정|보장)\s*(수익|수익률)")),
    ("단정적_수익예측", re.compile(r"(무조건|반드시|절대)\s*(오|수익|이득|벌)")),
    ("손실부인", re.compile(r"손실\s*(이)?\s*(없|없습니다|나지\s*않)")),
)

OUTPUT_DISCLAIMER = (
    "안내드린 내용은 참고용이며, 투자상품은 원금 손실이 발생할 수 있고 예금자보호 대상이 아닙니다. "
    "정확한 조건은 상담원 또는 영업점에서 확인해 주세요."
)


def scan_output(text: str) -> list[str]:
    """모델 답변에서 금융소비자보호 관점의 위험 표현을 찾아낸다."""
    return [name for name, pattern in _OUTPUT_VIOLATIONS if pattern.search(text)]


def apply_output_guard(text: str) -> tuple[str, list[str]]:
    """위험 표현이 있으면 고지 문구를 덧붙인다."""
    violations = scan_output(text)
    if not violations:
        return text, []
    return f"{text}\n\n> {OUTPUT_DISCLAIMER}", violations
