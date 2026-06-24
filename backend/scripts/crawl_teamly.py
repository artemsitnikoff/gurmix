"""Краулер базы «АССОРТИМЕНТ «ГУРМИКС»» из Teamly (публичный доступ, аноним).

Идёт по дереву через app.teamly.ru/api/v1/wiki/ql/article_content
(заголовок X-Account-Slug=s5-virtexfood). Собирает все узлы
(категории/подкатегории/товары) с путями и строит RAG-документы.

REST отдаёт таксономию (названия + иерархия), но НЕ rich-text тело статей
(оно в коллаборативном редакторе Teamly, анонимно недоступно). Поэтому документы
строятся из путей: товар + его категория/подкатегория, и обзорные карточки разделов
со списком позиций.

Запуск:  python backend/scripts/crawl_teamly.py
Выход:   backend/app/rag/assortment.json  (бандлится в образ, грузится в RAG).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

SLUG = "s5-virtexfood"
APP = "https://app.teamly.ru"
ROOT = "b8891bda-9d69-4c1e-8ad4-0bbd9064c7d1"
SPACE = "e467f0b7-f9f9-4cf8-8f2d-a9170ffb75dd"
HEADERS = {
    "X-Account-Slug": SLUG,
    "Content-Type": "application/json",
    "Origin": f"https://{SLUG}.teamly.ru",
    "Referer": f"https://{SLUG}.teamly.ru/",
}
OUT = Path(__file__).resolve().parent.parent / "app" / "rag" / "assortment.json"


def _post(path: str, body: dict, retries: int = 3) -> dict:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                APP + path, data=json.dumps(body).encode(), headers=HEADERS, method="POST"
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"POST {path} failed: {last}")


def _children(article_id: str) -> list[dict]:
    d = _post(
        "/api/v1/wiki/ql/article_content",
        {
            "query": {
                "__filter": {"article_id": article_id, "published": True},
                "__pagination": {"page": 1, "per_page": 300},
                "has_nested": True,
                "article": {"id": True, "title": True, "display_type": True},
            }
        },
    )
    out = []
    for r in (d or {}).get("data", []):
        a = r.get("article", {}) or {}
        title = (a.get("title") or "").strip()
        if not a.get("id") or not title:
            continue
        out.append({"id": a["id"], "title": title, "has_nested": bool(r.get("has_nested"))})
    return out


def main() -> None:
    nodes: list[dict] = []

    def walk(article_id: str, path: list[str], depth: int) -> None:
        for c in _children(article_id):
            node = {
                "id": c["id"],
                "title": c["title"],
                "path": path + [c["title"]],
                "is_leaf": not c["has_nested"],
                "depth": depth,
            }
            nodes.append(node)
            if c["has_nested"] and depth < 8:
                walk(c["id"], node["path"], depth + 1)

    print("Краулинг Teamly «АССОРТИМЕНТ ГУРМИКС»…")
    walk(ROOT, [], 0)

    products = [n for n in nodes if n["is_leaf"]]
    groups = [n for n in nodes if not n["is_leaf"]]
    categories = [n["title"] for n in nodes if n["depth"] == 0]
    print(f"узлов {len(nodes)} · товаров {len(products)} · разделов {len(groups)} · категорий {len(categories)}")

    def descendant_leaves(prefix: list[str]) -> list[dict]:
        n = len(prefix)
        return [p for p in products if p["path"][:n] == prefix]

    docs: list[dict] = []

    # Документ-обзор всего ассортимента.
    docs.append({
        "id": "_overview",
        "type": "overview",
        "title": "Ассортимент Гурмикс",
        "category": "",
        "path": "Ассортимент",
        "text": (
            f"Ассортимент Гурмикс: {len(products)} продуктов в {len(categories)} категориях — "
            + ", ".join(categories) + "."
        ),
    })

    # Документ на каждый раздел (категорию/подкатегорию) со списком позиций.
    for g in groups:
        leaves = descendant_leaves(g["path"])
        names = [le["path"][-1] for le in leaves]
        full = " › ".join(g["path"]) if g["path"] else "Ассортимент"
        docs.append({
            "id": g["id"],
            "type": "group",
            "title": g["path"][-1] if g["path"] else "Ассортимент",
            "category": g["path"][0] if g["path"] else "",
            "path": full,
            "text": f"Раздел ассортимента «{full}» — {len(names)} позиций: " + ", ".join(names) + ".",
        })

    # Документ на каждый товар.
    for p in products:
        full = " › ".join(p["path"])
        docs.append({
            "id": p["id"],
            "type": "product",
            "title": p["path"][-1],
            "category": p["path"][0] if p["path"] else "",
            "path": full,
            "text": f"Продукт Гурмикс «{p['path'][-1]}». Раздел: {full}.",
        })

    out = {
        "source": "Teamly АССОРТИМЕНТ «ГУРМИКС»",
        "space_id": SPACE,
        "root_id": ROOT,
        "stats": {
            "products": len(products),
            "groups": len(groups),
            "categories": len(categories),
            "documents": len(docs),
        },
        "categories": categories,
        "nodes": nodes,
        "documents": docs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"записано: {OUT}  ({len(docs)} документов)")


if __name__ == "__main__":
    main()
