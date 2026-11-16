from __future__ import annotations

import json
import re
from pathlib import Path


def normalize(value: str) -> str:
    readable = re.sub(r"\s+", " ", value).strip()
    readable = readable.replace("presentan lo mismo escenario", "presentan el mismo escenario")
    readable = readable.replace(
        "Algunos conjuntos de preguntas pueden tener más de una respuesta correcta. "
        "solución, mientras que otros podrían no tener una solución correcta.",
        "Algunos conjuntos de preguntas pueden tener más de una solución correcta, "
        "mientras que otros podrían no tener ninguna solución correcta.",
    )
    if readable.lower() == "si":
        return "Sí"
    return readable


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "translations" / "es.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        row["prompt_text"] = normalize(str(row["prompt_text"]))
        row["options"] = {key: normalize(str(value)) for key, value in row["options"].items()}
        row["comments"] = {
            key: normalize(str(value)) for key, value in row["comments"].items()
        }
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"Normalizadas {len(rows)} traducciones.")


if __name__ == "__main__":
    main()
