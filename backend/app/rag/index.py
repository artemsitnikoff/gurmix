"""BM25-ретрив поверх каталога ассортимента (backend/app/rag/assortment.json).

Чистый Python, без torch/transformers — индекс строится в памяти один раз при
старте (warm) или лениво при первом retrieve. Под русский — лёгкий префиксный
стемминг (первые 4 буквы), чтобы «соус/соусы/соусов» сводились к одной форме.

Документы готовит backend/scripts/crawl_teamly.py из базы Teamly.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "assortment.json"
_WORD = re.compile(r"[a-zа-яё0-9]+")


def _norm(s: str) -> str:
    return (s or "").lower().replace("ё", "е")


def _stem(w: str) -> str:
    # Префиксный «стем»: для каталога продуктов сводит словоформы (соус/соусы/
    # соусов → «соус»). Грубо, но для 186 коротких документов даёт высокий recall.
    return w[:4] if len(w) >= 4 else w


def _tok(s: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(_norm(s))]


class _BM25:
    def __init__(self, docs: list[dict], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        # Заголовок (название товара/раздела) весомее тела — повторяем ×3.
        self.corpus = [
            _tok((d.get("title", "") + " ") * 3 + d.get("text", "")) for d in docs
        ]
        self.N = len(self.corpus)
        self.avgdl = (sum(len(c) for c in self.corpus) / self.N) if self.N else 0.0
        df: Counter = Counter()
        for c in self.corpus:
            df.update(set(c))
        self.idf = {w: math.log(1 + (self.N - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.tf = [Counter(c) for c in self.corpus]
        self.k1, self.b = k1, b

    def search(self, query: str, k: int = 10) -> list[tuple[dict, float]]:
        q = _tok(query)
        if not q or not self.N:
            return []
        scored: list[tuple[float, int]] = []
        for i in range(self.N):
            tf = self.tf[i]
            dl = len(self.corpus[i]) or 1
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if not f:
                    continue
                idf = self.idf.get(w, 0.0)
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [(self.docs[i], round(s, 4)) for s, i in scored[:k]]


_index: _BM25 | None = None
_meta: dict = {}


def warm() -> int:
    """Построить индекс (идемпотентно). Возвращает число документов."""
    global _index, _meta
    if _index is not None:
        return _index.N
    try:
        data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except OSError as e:
        logger.warning("[rag] assortment.json не найден (%s) — RAG пуст", e)
        _index = _BM25([])
        return 0
    _meta = data.get("stats", {})
    _index = _BM25(data.get("documents", []))
    return _index.N


def size() -> int:
    return warm()


def retrieve(query: str, k: int = 10) -> list[tuple[dict, float]]:
    """Топ-k документов ассортимента по BM25. Каждый — (doc, score)."""
    if _index is None:
        warm()
    return _index.search(query, k=k) if _index else []
