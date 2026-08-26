# 금융권 고객센터 AI 상담 에이전트

가상의 **한결은행** 고객센터를 가정한 대화형 AI 상담 에이전트입니다.
기술 면접에서 "에이전트를 어떻게 설계했고, 왜 그렇게 했는지"를 설명하기 좋도록
도구 호출·RAG·가드레일·상태 관리를 최소한의 코드로 모두 담았습니다.

```
Streamlit UI  ──▶  LangGraph 그래프  ──▶  Claude (langchain-anthropic)
                        │
                        ├── 가드레일 (PII 마스킹 / 입력 차단 / 출력 검사)
                        ├── 업무 도구 (계좌·거래·카드·한도·상담원 연결)
                        └── FAQ 검색 (BM25 리트리버)
```

> 모듈 구조와 한 턴의 실행 흐름을 단계별로 추적한 문서: [`docs/ai-agent-architecture.md`](../docs/ai-agent-architecture.md)

## 기술 스택

| 영역 | 선택 | 이유 |
| --- | --- | --- |
| 에이전트 프레임워크 | **LangGraph 1.x** | 조건부 분기·루프를 그래프로 명시할 수 있어 "가드레일을 LLM *앞*에 둔다"는 설계를 코드로 드러낼 수 있음 |
| LLM | **Claude Opus 5** (`langchain-anthropic`) | 도구 호출 정확도가 높고, 긴 대화에서도 지시(금지사항)를 잘 지킴 |
| UI | **Streamlit** | 상담 화면·도구 호출 로그·가드레일 로그를 한 화면에서 데모하기에 가장 빠름 |
| 설정 | **pydantic-settings** | 환경변수 검증과 타입 안정성. API 키는 코드에 두지 않음 |
| 검색 | 자체 **BM25** 리트리버 | FAQ 12건 규모에서 벡터 DB는 과설계. 한국어 음절 bigram 색인으로 조사·어미 변화를 흡수 |
| 테스트 | **pytest** (46 케이스) | 가짜 모델을 주입해 **API 호출 없이** 그래프 전체를 검증 |

## 실행 방법

```bash
cd ai_agent

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env      # ANTHROPIC_API_KEY 입력
streamlit run app.py      # http://localhost:8501
```

테스트와 린트:

```bash
pytest          # 46 passed
ruff check .
```

## 그래프 구조

```
START ─→ guard ─┬─(차단)─────────────────────────────────→ END
                └─→ agent ─┬─(도구 호출)→ tools ─┘(다시 agent)
                           └─(최종 답변)─────────────────→ END
```

| 노드 | 역할 |
| --- | --- |
| `guard` | LLM 호출 **전에** 실행되는 결정적 방어선. PII 마스킹 + 금지 요청 차단 |
| `agent` | 도구가 바인딩된 Claude 호출. 최종 답변에는 출력 가드레일 적용 |
| `tools` | LangGraph 기본 `ToolNode`. 도구 실행 결과를 대화에 되돌림 |

대화 이력은 체크포인터에 `thread_id` 단위로 저장되므로 UI는 메시지 배열을
직접 관리하지 않습니다(`build_graph` → `InMemorySaver`).

## 설계에서 신경 쓴 부분

### 1. LLM은 "누구의" 데이터를 볼지 결정할 수 없다

도구는 인증된 세션의 `customer_id`에 **클로저로 바인딩**되어 생성됩니다
(`CustomerToolkit.as_tools`). 모델이 만들어내는 인자에는 조회 대상 고객이
포함되지 않으므로, 프롬프트 인젝션으로 타인 계좌를 조회하는 경로 자체가
존재하지 않습니다. 계좌번호처럼 모델이 넘기는 인자는 서버에서 본인 소유인지
다시 검증합니다.

```python
# tests/test_tools.py
def test_transactions_reject_other_customers_account(tools):
    result = tools["get_transactions"].invoke({"account_no": "210-991-004512"})
    assert "본인 명의 계좌가 아니" in result
```

### 2. 가드레일은 LLM 판단에 맡기지 않는다

프롬프트에 "비밀번호를 묻지 마세요"라고 쓰는 것만으로는 부족합니다.
`guardrails.py`는 정규식 기반의 **결정적** 방어선입니다.

- **PII 마스킹**: 주민등록번호·카드번호·계좌번호·전화번호·이메일·인증정보를
  LLM에 보내기 *전에* 가립니다. 원문은 프롬프트에도, 대화 이력에도, 화면에도
  남지 않습니다.
- **입력 차단**: 비밀번호/OTP 노출, 불법 금융(대포통장·명의대여), 투자 권유 요구는
  모델을 아예 호출하지 않고 고정 응답으로 처리합니다.
- **출력 검사**: "원금 보장", "확정 수익" 같은 금융소비자보호법상 위험 표현을
  탐지해 고지 문구를 덧붙입니다.

계좌번호 마스킹은 뒤 4자리를 남깁니다(`110-***-**7890`). 보안을 지키면서도
도구가 뒤 4자리로 본인 계좌를 식별할 수 있게 하기 위한 절충입니다.

### 3. 되돌릴 수 없는 처리는 확인 후에

`report_card_lost`, `request_limit_increase`처럼 상태를 바꾸는 도구는
프롬프트에서 "고객 동의를 얻은 뒤 호출"하도록 지시하고, 실행 결과는 접수번호와
함께 사이드바 감사 로그에 남습니다. 중복 신고는 도구 레벨에서 멱등 처리합니다.

### 4. 무한 루프 방지

도구 호출 라운드가 `max_tool_iterations`에 도달하면 도구를 뺀 모델로 마지막
답변을 만들어, 대화가 끊기지 않으면서도 비용이 발산하지 않게 합니다.

### 5. Claude Opus 5 관련 주의점 (코드에 반영됨)

- `temperature` / `top_p` 등 샘플링 파라미터를 넘기면 **400 에러**가 납니다. 넘기지 않습니다.
- thinking이 기본으로 켜져 있으므로 `thinking` 파라미터를 따로 설정하지 않습니다.
- 시스템 프롬프트에는 호출마다 바뀌는 값(현재 시각 등)을 넣지 않아 캐시 프리픽스를 깨뜨리지 않습니다.

## 프로젝트 구조

```
ai_agent/
├── app.py                        # Streamlit UI (스트리밍, 도구 로그, 감사 로그)
├── pyproject.toml
├── .env.example
├── src/finance_agent/
│   ├── config.py                 # pydantic-settings 기반 설정
│   ├── prompts.py                # 시스템 프롬프트
│   ├── guardrails.py             # PII 마스킹 / 입력 차단 / 출력 검사
│   ├── retriever.py              # 한국어 BM25 FAQ 리트리버
│   ├── graph.py                  # LangGraph 그래프 조립
│   ├── tools/banking.py          # 업무 도구 7종
│   └── data/                     # 목 고객 데이터 + FAQ 지식베이스
└── tests/                        # 46개 테스트 (API 호출 없음)
```

## 도구 목록

| 도구 | 설명 | 상태 변경 |
| --- | --- | --- |
| `search_faq` | 규정·절차·수수료 FAQ 검색 (BM25) | |
| `get_accounts` | 본인 계좌·잔액·이체한도 조회 | |
| `get_transactions` | 본인 계좌 거래내역 조회 (마스킹 번호 허용) | |
| `get_cards` | 보유 카드와 상태 조회 | |
| `report_card_lost` | 카드 분실신고 및 즉시 사용정지 | ✅ |
| `request_limit_increase` | 이체한도 상향 접수 | ✅ |
| `escalate_to_human` | 상담원 연결 (상담 요약 인계) | ✅ |

## 데모 시나리오

1. `제 계좌 잔액이랑 최근 거래 알려주세요` → 도구 2회 호출 후 요약 답변
2. `카드를 잃어버렸어요` → FAQ 안내 + 대상 카드 확인 → 동의 후 분실신고 접수
3. `이체한도를 1일 2천만원으로 올려주세요` → 접수 + 영업점 방문 필요 안내
4. `비밀번호는 483921 이에요` → **모델 호출 없이 차단** + 비밀번호 변경 안내
5. `어떤 주식 살까요?` → 투자 권유 거절 + 상담원 연결 제안

## 한계와 다음 단계

- 데이터는 JSON 목 데이터입니다. 실제로는 코어뱅킹 API 어댑터로 교체해야 합니다.
- 체크포인터가 인메모리라 프로세스가 죽으면 대화가 사라집니다.
  운영에서는 `langgraph-checkpoint-postgres`로 교체합니다.
- FAQ가 수천 건 규모가 되면 `retriever.search()` 시그니처를 유지한 채
  내부를 pgvector / OpenSearch로 교체하면 됩니다.
- 가드레일 룰은 정규식 기반이라 우회 가능성이 있습니다. 운영에서는
  분류 모델 또는 Claude 기반 2차 심사를 룰 뒤에 덧붙이는 2단 구성이 적절합니다.
- 답변 품질 회귀 테스트(LLM-as-judge)와 도구 호출 정확도 지표가 아직 없습니다.
