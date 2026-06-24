"""Лёгкий RAG поверх каталога ассортимента Гурмикс (BM25, без тяжёлых ML-зависимостей)."""
from app.rag.index import retrieve, size, warm

__all__ = ["retrieve", "size", "warm"]
