"""FAQ 검색용 경량 BM25 리트리버.

임베딩 API 나 벡터 DB 없이 순수 파이썬으로 동작한다. 선택 이유는 두 가지다.

* FAQ 12건 수준에서는 벡터 검색의 이점이 없고, 오프라인/무비용으로 테스트할 수 있다.
* 한국어는 공백 토큰만으로는 재현율이 낮아, 음절 bigram 을 함께 색인해 조사·어미 변화를
  흡수한다("이체한도" <-> "이체 한도 상향").

운영 환경에서 문서 수가 늘어나면 `search()` 시그니처를 유지한 채 내부를
pgvector / OpenSearch / Chroma 로 교체하면 된다.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

_TOKEN = re.compile(r"[0-9a-zA-Z]+|[가-힣]+")


@dataclass(frozen=True)
class FaqDocument:
    id: str
    category: str
    title: str
    tags: tuple[str, ...]
    content: str

    @property
    def searchable_text(self) -> str:
        return f"{self.title} {' '.join(self.tags)} {self.category} {self.content}"


def tokenize(text: str) -> list[str]:
    """단어 토큰 + 한글 음절 bigram."""
    tokens: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if re.fullmatch(r"[가-힣]+", raw):
            if len(raw) == 1:
                continue
            tokens.append(raw)
            tokens.extend(raw[i : i + 2] for i in range(len(raw) - 1))
        elif len(raw) > 1:
            tokens.append(raw)
    return tokens


class BM25Retriever:
    """Okapi BM25 (k1=1.5, b=0.75)."""

    def __init__(self, documents: list[FaqDocument], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self._tf: list[Counter[str]] = [Counter(tokenize(d.searchable_text)) for d in documents]
        self._lengths = [sum(tf.values()) for tf in self._tf]
        self._avg_len = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(documents)
        self._idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()
        }

    def search(self, query: str, top_k: int = 3) -> list[tuple[FaqDocument, float]]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[FaqDocument, float]] = []
        for idx, tf in enumerate(self._tf):
            length = self._lengths[idx] or 1
            score = 0.0
            for term in query_terms:
                freq = tf.get(term)
                if not freq:
                    continue
                denom = freq + self.k1 * (1 - self.b + self.b * length / (self._avg_len or 1))
                score += self._idf.get(term, 0.0) * freq * (self.k1 + 1) / denom
            if score > 0:
                scored.append((self.documents[idx], score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


def load_faq_documents(path: Path | None = None) -> list[FaqDocument]:
    raw = json.loads((path or DATA_DIR / "faq.json").read_text(encoding="utf-8"))
    return [
        FaqDocument(
            id=item["id"],
            category=item["category"],
            title=item["title"],
            tags=tuple(item.get("tags", [])),
            content=item["content"],
        )
        for item in raw
    ]


@lru_cache(maxsize=1)
def get_retriever() -> BM25Retriever:
    """FAQ 인덱스는 프로세스당 한 번만 만든다."""
    return BM25Retriever(load_faq_documents())
