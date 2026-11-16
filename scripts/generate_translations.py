from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MARKER_PATTERN = re.compile(r"<<<MB230S(\d{6})>>>")


@dataclass(frozen=True)
class Segment:
    index: int
    question_id: str
    field: str
    key: str
    text: str


def split_text(text: str, limit: int = 2800) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = max(
            remaining.rfind("\n", 0, limit),
            remaining.rfind(". ", 0, limit),
            remaining.rfind(" ", 0, limit),
        )
        if split_at < limit // 2:
            split_at = limit
        elif remaining[split_at : split_at + 2] == ". ":
            split_at += 2
        else:
            split_at += 1
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


def create_segments(records: list[dict]) -> tuple[list[Segment], dict[tuple[str, str, str], list[int]]]:
    segments: list[Segment] = []
    groups: dict[tuple[str, str, str], list[int]] = {}

    def add(question_id: str, field: str, key: str, text: str) -> None:
        group = (question_id, field, key)
        groups[group] = []
        readable_text = re.sub(r"\s+", " ", text).strip()
        for chunk in split_text(readable_text):
            index = len(segments)
            segments.append(Segment(index, question_id, field, key, chunk))
            groups[group].append(index)

    for record in records:
        question_id = str(record["id"])
        add(question_id, "prompt_text", "", str(record["prompt_text"]))
        for option in record.get("options", []):
            add(question_id, "options", str(option["key"]), str(option["text"]))
        for comment in record.get("community_comments", []):
            add(question_id, "comments", str(comment["position"]), str(comment["raw_text"]))
    return segments, groups


def create_batches(segments: list[Segment], limit: int = 3900) -> list[list[Segment]]:
    batches: list[list[Segment]] = []
    current: list[Segment] = []
    current_size = 0
    for segment in segments:
        estimated = len(segment.text) + 24
        if current and current_size + estimated > limit:
            batches.append(current)
            current = []
            current_size = 0
        current.append(segment)
        current_size += estimated
    if current:
        batches.append(current)
    return batches


def translate_batch(batch: list[Segment]) -> dict[int, str]:
    source = "\n".join(f"<<<MB230S{segment.index:06d}>>>\n{segment.text}" for segment in batch)
    payload = urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "es", "dt": "t", "q": source}
    ).encode()
    request = urllib.request.Request(
        TRANSLATE_URL,
        data=payload,
        headers={"User-Agent": "Mozilla/5.0 MB230-static-translation-builder"},
    )
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
            translated = "".join(fragment[0] for fragment in data[0])
            matches = list(MARKER_PATTERN.finditer(translated))
            result: dict[int, str] = {}
            for position, match in enumerate(matches):
                start = match.end()
                end = matches[position + 1].start() if position + 1 < len(matches) else None
                result[int(match.group(1))] = translated[start:end].strip("\r\n")
            expected = {segment.index for segment in batch}
            if set(result) != expected or any(not result[index].strip() for index in expected):
                raise RuntimeError("El servicio no conservó los marcadores del lote")
            return result
        except (OSError, ValueError, KeyError, RuntimeError, urllib.error.HTTPError) as exc:
            last_error = exc
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"No se pudo traducir un lote tras varios intentos: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera el corpus español separado del dataset canónico MB-230."
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    source_path = root / "data" / "canonical" / "questions.jsonl"
    output_path = root / "data" / "translations" / "es.jsonl"
    records = [json.loads(line) for line in source_path.read_text(encoding="utf-8").splitlines()]
    segments, groups = create_segments(records)
    batches = create_batches(segments)
    translated_chunks: dict[int, str] = {}

    print(f"Traduciendo {len(records)} preguntas en {len(batches)} lotes...")
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as executor:
        futures = {executor.submit(translate_batch, batch): number for number, batch in enumerate(batches, 1)}
        completed = 0
        for future in as_completed(futures):
            translated_chunks.update(future.result())
            completed += 1
            if completed % 20 == 0 or completed == len(batches):
                print(f"  {completed}/{len(batches)} lotes")

    output_records: list[dict] = []
    for record in records:
        question_id = str(record["id"])

        def translated(field: str, key: str = "", question_id: str = question_id) -> str:
            indexes = groups[(question_id, field, key)]
            return "".join(translated_chunks[index] for index in indexes).strip()

        output_records.append(
            {
                "question_id": question_id,
                "prompt_text": translated("prompt_text"),
                "options": {
                    str(option["key"]): (
                        "Sí"
                        if str(option["text"]).strip().lower() == "yes"
                        else translated("options", str(option["key"]))
                    )
                    for option in record.get("options", [])
                },
                "comments": {
                    str(comment["position"]): translated("comments", str(comment["position"]))
                    for comment in record.get("community_comments", [])
                },
                "translation_method": "machine-google",
            }
        )

    if len(output_records) != 463 or any(not row["prompt_text"] for row in output_records):
        raise RuntimeError("La salida no contiene las 463 traducciones completas")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in output_records),
        encoding="utf-8",
    )
    print(f"Corpus completo guardado en {output_path}")


if __name__ == "__main__":
    main()
