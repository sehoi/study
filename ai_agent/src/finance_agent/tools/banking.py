"""에이전트가 사용할 업무 도구 모음.

핵심 설계 원칙: **LLM 은 "누구의" 데이터를 볼지 결정할 수 없다.**

도구는 인증된 세션의 `customer_id` 에 클로저로 바인딩되어 생성된다. 모델이 만들어낸
인자에는 조회 대상 고객이 포함되지 않으므로, 프롬프트 인젝션으로 타인의 계좌를
조회하는 경로 자체가 존재하지 않는다. 계좌번호처럼 모델이 넘기는 인자는 항상
본인 소유인지 서버에서 다시 검증한다(`_resolve_account`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, tool

from finance_agent.retriever import get_retriever

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_customers(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or DATA_DIR / "customers.json").read_text(encoding="utf-8"))


def _won(amount: int) -> str:
    return f"{amount:,}원"


@dataclass
class ActionRecord:
    """세션 중 실제로 접수된 업무(감사 로그용)."""

    ticket: str
    action: str
    detail: str
    at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


class CustomerToolkit:
    """인증된 고객 한 명에게 바인딩된 도구 집합."""

    def __init__(self, customer_id: str, customers: dict[str, Any] | None = None) -> None:
        self._customers = customers if customers is not None else load_customers()
        if customer_id not in self._customers:
            raise KeyError(f"알 수 없는 고객 ID: {customer_id}")
        self.customer_id = customer_id
        self.actions: list[ActionRecord] = []

    # ---------------------------------------------------------------- 내부 헬퍼
    @property
    def customer(self) -> dict[str, Any]:
        return self._customers[self.customer_id]

    def _next_ticket(self, prefix: str) -> str:
        return f"{prefix}-{datetime.now():%Y%m%d}-{len(self.actions) + 1:03d}"

    def _record(self, prefix: str, action: str, detail: str) -> ActionRecord:
        record = ActionRecord(ticket=self._next_ticket(prefix), action=action, detail=detail)
        self.actions.append(record)
        return record

    def _resolve_account(self, account_no: str) -> dict[str, Any] | None:
        """모델이 넘긴 계좌번호를 본인 계좌 중에서 찾는다.

        사용자 입력은 가드레일에서 마스킹되므로(`110-***-**7890`) 모델이 전체
        번호를 모를 수 있다. 숫자만 추려 뒤 4자리로도 매칭한다.
        """
        digits = "".join(ch for ch in account_no if ch.isdigit())
        if not digits:
            return None
        for account in self.customer["accounts"]:
            own = "".join(ch for ch in account["account_no"] if ch.isdigit())
            if own == digits or (len(digits) >= 4 and own.endswith(digits[-4:])):
                return account
        return None

    def _find_card(self, card_last4: str) -> dict[str, Any] | None:
        digits = "".join(ch for ch in card_last4 if ch.isdigit())[-4:]
        return next((c for c in self.customer["cards"] if c["last4"] == digits), None)

    # ---------------------------------------------------------------- 도구 정의
    def as_tools(self) -> list[BaseTool]:
        customer = self.customer

        @tool
        def search_faq(query: str) -> str:
            """은행 이용 안내·규정·수수료·절차에 대한 FAQ 를 검색한다.

            고객의 개인 정보가 아니라 '일반적인 안내'가 필요할 때 사용한다.
            예: 이체한도 상향 방법, 예금자보호 한도, 해외송금 수수료, 영업시간.

            Args:
                query: 검색할 질문이나 키워드.
            """
            hits = get_retriever().search(query, top_k=3)
            if not hits:
                return "관련 FAQ 를 찾지 못했습니다. 상담원 연결을 안내하세요."
            return "\n\n".join(
                f"[{doc.id}] {doc.title} ({doc.category})\n{doc.content}" for doc, _ in hits
            )

        @tool
        def get_accounts() -> str:
            """인증된 고객 본인의 보유 계좌와 잔액, 이체한도를 조회한다."""
            lines = [f"{customer['name']} 고객님({customer['grade']})의 보유 계좌"]
            for acc in customer["accounts"]:
                extra = ""
                if acc.get("maturity_date"):
                    extra = f", 만기 {acc['maturity_date']}, 금리 {acc['interest_rate']}%"
                lines.append(
                    f"- {acc['account_no']} | {acc['product']} ({acc['type']}) | "
                    f"잔액 {_won(acc['balance'])} | 상태 {acc['status']}{extra}"
                )
            limits = customer["limits"]
            lines.append(
                f"이체한도: 1회 {_won(limits['once_transfer_limit'])} / "
                f"1일 {_won(limits['daily_transfer_limit'])}"
            )
            return "\n".join(lines)

        @tool
        def get_transactions(account_no: str, limit: int = 5) -> str:
            """본인 계좌의 최근 거래내역을 조회한다.

            Args:
                account_no: 조회할 계좌번호. 마스킹된 형태나 뒤 4자리만으로도 조회된다.
                limit: 가져올 거래 건수(기본 5, 최대 20).
            """
            account = self._resolve_account(account_no)
            if account is None:
                owned = ", ".join(a["account_no"] for a in customer["accounts"])
                return f"본인 명의 계좌가 아니거나 존재하지 않습니다. 조회 가능한 계좌: {owned}"

            history = customer["transactions"].get(account["account_no"], [])
            if not history:
                return f"{account['account_no']} 계좌의 거래내역이 없습니다."

            rows = history[: max(1, min(limit, 20))]
            lines = [f"{account['account_no']} ({account['product']}) 최근 거래 {len(rows)}건"]
            for tx in rows:
                sign = "입금" if tx["amount"] > 0 else "출금"
                lines.append(
                    f"- {tx['date']} | {tx['description']} | {sign} "
                    f"{_won(abs(tx['amount']))} | 잔액 {_won(tx['balance'])}"
                )
            return "\n".join(lines)

        @tool
        def get_cards() -> str:
            """본인 명의 카드 목록과 상태(정상/분실신고), 당월 사용액을 조회한다."""
            if not customer["cards"]:
                return "보유 중인 카드가 없습니다."
            return "\n".join(
                f"- {c['brand']} (끝 4자리 {c['last4']}) | 상태 {c['status']} | "
                f"당월 사용 {_won(c['monthly_used'])}"
                for c in customer["cards"]
            )

        @tool
        def report_card_lost(card_last4: str) -> str:
            """카드 분실·도난 신고를 접수하고 즉시 사용을 정지한다.

            되돌리기 어려운 처리이므로, 반드시 고객에게 대상 카드를 확인받은 뒤 호출한다.

            Args:
                card_last4: 분실 신고할 카드번호 뒤 4자리.
            """
            card = self._find_card(card_last4)
            if card is None:
                available = ", ".join(f"{c['brand']}({c['last4']})" for c in customer["cards"])
                return f"해당 카드를 찾을 수 없습니다. 보유 카드: {available or '없음'}"
            if card["status"] == "분실신고":
                return f"{card['brand']}(끝 4자리 {card['last4']})는 이미 분실신고된 카드입니다."

            card["status"] = "분실신고"
            record = self._record(
                "LOST", "카드 분실신고", f"{card['brand']} (끝 4자리 {card['last4']})"
            )
            return (
                f"분실신고가 접수되었습니다. 접수번호 {record.ticket}\n"
                f"대상: {card['brand']} (끝 4자리 {card['last4']})\n"
                "즉시 사용정지 처리되었습니다.\n"
                "재발급을 원하시면 앱 또는 영업점에서 신청할 수 있으며 3~5영업일 내 배송됩니다."
            )

        @tool
        def request_limit_increase(daily_limit: int, reason: str) -> str:
            """이체한도 상향을 접수한다.

            Args:
                daily_limit: 고객이 요청한 1일 이체한도(원).
                reason: 상향이 필요한 사유.
            """
            current = customer["limits"]["daily_transfer_limit"]
            if daily_limit <= current:
                return f"현재 1일 한도({_won(current)})보다 크지 않아 접수할 수 없습니다."

            record = self._record(
                "LMT", "이체한도 상향 신청", f"1일 {_won(current)} → {_won(daily_limit)} ({reason})"
            )
            if daily_limit > 10_000_000:
                note = (
                    "1일 1천만원을 초과하는 한도는 비대면으로 처리할 수 없어 "
                    "신분증과 자금 출처 증빙을 지참한 영업점 방문이 필요합니다."
                )
            else:
                note = "심사 후 영업일 기준 1일 이내에 결과를 알림으로 안내드립니다."
            return f"한도 상향 신청이 접수되었습니다. 접수번호 {record.ticket}\n{note}"

        @tool
        def escalate_to_human(topic: str, summary: str) -> str:
            """사람 상담원에게 연결한다.

            다음 경우에 사용한다: 규정상 AI 가 처리할 수 없는 업무, 대출·투자 상담,
            민원·불만 제기, 두 번 이상 안내해도 해결되지 않은 문의.

            Args:
                topic: 상담 주제(예: 대출 상담, 민원 접수).
                summary: 지금까지의 상담 내용 요약. 상담원에게 그대로 전달된다.
            """
            record = self._record("CS", f"상담원 연결 - {topic}", summary)
            return (
                f"상담원 연결이 접수되었습니다. 접수번호 {record.ticket}\n"
                "상담 가능 시간: 평일 09:00~18:00 (분실·사고 신고는 24시간)\n"
                "지금까지의 상담 내용이 상담원에게 전달되어 처음부터 다시 말씀하지 않으셔도 됩니다."
            )

        return [
            search_faq,
            get_accounts,
            get_transactions,
            get_cards,
            report_card_lost,
            request_limit_increase,
            escalate_to_human,
        ]
