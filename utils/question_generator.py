from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from openai import OpenAI


@dataclass
class ChapterQuestionSet:
    chapter_title: str
    topic: str
    questions: List[Dict[str, Any]]


class GenerationError(Exception):
    """Raised when model output cannot be parsed."""


def build_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def generate_questions_for_chapter(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_template: str,
    chapter_title: str,
    chapter_text: str,
    topic: str,
    num_questions: int,
    min_questions_required: int,
    max_output_tokens: int,
) -> ChapterQuestionSet:
    user_prompt = _render_user_prompt(
        user_template=user_template,
        topic=topic,
        chapter_title=chapter_title,
        chapter_text=chapter_text,
        num_questions=num_questions,
    )
    last_error: str | None = None
    for attempt in range(2):
        attempt_prompt = user_prompt
        if attempt == 1:
            attempt_prompt = (
                f"{user_prompt}\n\n"
                "CRITICAL: Your previous response was invalid or empty. "
                f"Return exactly {num_questions} questions. "
                "Return only a strict JSON object, no markdown or prose."
            )

        request_payload = {
            "model": model,
            "max_output_tokens": max_output_tokens,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": attempt_prompt}]},
            ],
        }

        response = client.responses.create(**request_payload)
        raw_text = response.output_text.strip()
        parsed = _parse_or_repair_json(
            client=client,
            model=model,
            raw_text=raw_text,
            chapter_title=chapter_title,
        )
        question_set = _normalize_question_set(
            payload=parsed,
            fallback_chapter_title=chapter_title,
            fallback_topic=topic,
        )
        if len(question_set.questions) >= min_questions_required:
            return question_set
        last_error = (
            f"Model returned {len(question_set.questions)} questions; "
            f"minimum required is {min_questions_required}."
        )

    raise GenerationError(
        f"Could not generate valid questions for chapter '{chapter_title}'. {last_error or ''}".strip()
    )


def _strip_markdown_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _parse_or_repair_json(
    client: OpenAI,
    model: str,
    raw_text: str,
    chapter_title: str,
) -> Dict[str, Any]:
    cleaned = _strip_markdown_code_fence(raw_text)
    parsed = _try_parse_json(cleaned)
    if parsed is not None:
        return parsed

    extracted = _extract_first_json_object(cleaned)
    if extracted is not None:
        parsed = _try_parse_json(extracted)
        if parsed is not None:
            return parsed

    repaired = _repair_json_with_model(client=client, model=model, raw_text=cleaned)
    parsed = _try_parse_json(_strip_markdown_code_fence(repaired))
    if parsed is not None:
        return parsed

    extracted_repaired = _extract_first_json_object(repaired)
    if extracted_repaired is not None:
        parsed = _try_parse_json(extracted_repaired)
        if parsed is not None:
            return parsed

    raise GenerationError(f"Model returned non-JSON output for chapter '{chapter_title}'.")


def _try_parse_json(text: str) -> Dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def _repair_json_with_model(client: OpenAI, model: str, raw_text: str) -> str:
    prompt = (
        "Convert the following content into strict JSON only. "
        "Return a single JSON object with keys: chapter_title, topic, questions. "
        "questions must be an array of objects with keys: id, difficulty, question, answer. "
        "No markdown, no explanation, JSON only.\n\n"
        f"CONTENT:\n{raw_text}"
    )
    response = client.responses.create(
        model=model,
        max_output_tokens=1600,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
    )
    return response.output_text.strip()


def _normalize_question_set(
    payload: Dict[str, Any],
    fallback_chapter_title: str,
    fallback_topic: str,
) -> ChapterQuestionSet:
    chapter_title = str(payload.get("chapter_title") or "").strip() or fallback_chapter_title
    topic = str(payload.get("topic") or "").strip() or fallback_topic
    raw_questions = payload.get("questions")

    questions: List[Dict[str, Any]] = []
    if isinstance(raw_questions, list):
        for idx, item in enumerate(raw_questions, start=1):
            if not isinstance(item, dict):
                continue
            question_text = str(item.get("question") or "").strip()
            if not question_text:
                continue
            difficulty = str(item.get("difficulty") or "medium").strip().lower()
            if difficulty not in {"easy", "medium", "hard"}:
                difficulty = "medium"
            qid = item.get("id", idx)
            answer_text = str(item.get("answer") or "").strip()
            if not answer_text:
                continue
            questions.append(
                {
                    "id": qid,
                    "difficulty": difficulty,
                    "question": question_text,
                    "answer": answer_text,
                }
            )

    return ChapterQuestionSet(chapter_title=chapter_title, topic=topic, questions=questions)


def _render_user_prompt(
    user_template: str,
    topic: str,
    chapter_title: str,
    chapter_text: str,
    num_questions: int,
) -> str:
    # Replace only supported placeholders so literal JSON braces in YAML stay intact.
    return (
        user_template.replace("{topic}", topic)
        .replace("{chapter_title}", chapter_title)
        .replace("{chapter_text}", chapter_text)
        .replace("{num_questions}", str(num_questions))
    )
