"""LLM-as-judge — асессор полезности ответа (порт teplodar src/eval/judge.py).

Оценивает, насколько ответ бота полезен пользователю: дёргает Claude CLI
(модель Haiku по умолчанию — settings.claude_judge_model), парсит строгий JSON
{"score": 0-100, "verdict": "..."} и возвращает dict или None.

Best-effort: на любой сбой (CLI упал/таймаут/битый JSON/нечисловой score)
возвращает None — запись просто остаётся без оценки. Запускается АСИНХРОННО в
фоне уже ПОСЛЕ выдачи ответа пользователю (см. api/chat.py), поэтому на латентность
чата не влияет.
"""
from __future__ import annotations

import json
import logging
import re

from app.core.claude_cli import ClaudeCLIError, call_cli
from app.core.config import settings

logger = logging.getLogger(__name__)

# Python .format → фигурные скобки JSON в примере удвоены.
_PROMPT = """Ты — асессор ответов AI-ассистента компании «Гурмикс» (профессиональные продукты для кухни: соусы, маринады, панировки, основы для HoReCa, ритейла и фабрик-кухонь).
Оцени, насколько ответ бота ПОЛЕЗЕН для пользователя — содержит ли он информацию, которую тот реально хотел получить.

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

ОТВЕТ БОТА:
{answer}

Критерии оценки score (0-100):
- 90-100: точный, конкретный, по делу, структурированный. Пользователь получил именно то, что хотел.
- 70-89: правильное направление, но не вся информация / расплывчато / общие фразы вместо конкретики.
- 40-69: ответ касается темы, но не отвечает на конкретный вопрос. Полу-помощь.
- 10-39: бот ушёл в сторону / отказался отвечать, когда мог помочь / выдумал факты / шаблонное «оставьте заявку» там, где можно было ответить.
- 0-9: ответ совершенно нерелевантный или это ошибка.

ВАЖНО:
- Если бот честно сказал, что точных данных о конкретном артикуле/цене/контакте дистрибьютора Гурмикс у него нет, и предложил оставить заявку — это ПРАВИЛЬНО (75-90), не штрафуй: бот не должен выдумывать конкретику Гурмикс.
- Если бот ВЫДУМАЛ продукт / состав / норму / цену / контакт — резкий штраф (0-20).
- Длина ответа не важна — оценивай ПОЛЬЗУ для пользователя.

Верни СТРОГО JSON без markdown-fence:
{{"score": <0-100>, "verdict": "<одна короткая фраза, до 200 символов, почему такая оценка>"}}
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def judge_answer(question: str, answer: str, model: str = "") -> dict | None:
    """Оценить полезность ответа. Возвращает {"score": int, "verdict": str} или None.

    Никогда не бросает — все сбои логируются на debug и дают None.
    """
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer:
        return None
    # Кап длины — судье достаточно оценить пользу, не нужен весь ответ целиком
    # (страхует от раздувания вызова и таймаута на очень длинных ответах).
    question = question[:4000]
    answer = answer[:8000]

    prompt = _PROMPT.format(question=question, answer=answer)
    use_model = model or settings.claude_judge_model

    try:
        text = call_cli(prompt, model=use_model)
    except ClaudeCLIError as e:
        logger.debug("[judge] CLI failed: %s", e)
        return None

    m = _JSON_BLOCK_RE.search(text)
    if not m:
        logger.debug("[judge] no JSON block in output: %.120s", text)
        return None
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError) as e:
        logger.debug("[judge] bad JSON (%s): %.120s", e, text)
        return None

    score = data.get("score")
    if not isinstance(score, (int, float)):
        return None
    score = max(0, min(100, int(score)))
    verdict = str(data.get("verdict") or "")[:500]
    return {"score": score, "verdict": verdict}
