from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader

HEADER_BOTTOM = 60.0
# Footer text starts around y=809. Cropping at 805 keeps the source material
# intact while preventing "Page N of 997" from leaking into option text.
FOOTER_TOP = 805.0
QUESTION_COUNT = 463
OPTION_RE = re.compile(r"(?ms)^[ \t]*([A-Z])\)[ \t]+.*?(?=^[ \t]*[A-Z]\)[ \t]+|\Z)")
CORRECT_RE = re.compile(r"\s*\(Correct Answer\)\s*", re.I)


@dataclass(frozen=True)
class Anchor:
    number: int
    page_index: int
    top: float


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: dict[str, Any]) -> str:
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256_bytes(encoded)


def load_anchors(reader: PdfReader) -> list[Anchor]:
    anchors: list[Anchor] = []
    destinations = reader.named_destinations
    for number in range(1, QUESTION_COUNT + 1):
        destination = destinations.get(f"id-{number}")
        if destination is None:
            raise ValueError(f"Missing named destination id-{number}")
        page_index = reader.get_destination_page_number(destination)
        page_height = float(reader.pages[page_index].mediabox.height)
        pdf_top = float(destination.get("/Top", page_height - HEADER_BOTTOM))
        anchors.append(Anchor(number, page_index, page_height - pdf_top))
    return anchors


def fragment_bboxes(
    anchors: list[Anchor], number: int, page_sizes: list[tuple[float, float]]
) -> list[dict[str, Any]]:
    start = anchors[number - 1]
    if number < len(anchors):
        end = anchors[number]
        end_page = end.page_index
        end_top = end.top
    else:
        end_page = len(page_sizes) - 1
        end_top = FOOTER_TOP
    fragments: list[dict[str, Any]] = []
    for page_index in range(start.page_index, end_page + 1):
        width, height = page_sizes[page_index]
        top = start.top if page_index == start.page_index else HEADER_BOTTOM
        bottom = end_top if page_index == end_page else min(FOOTER_TOP, height - 25)
        if bottom <= top + 1:
            continue
        fragments.append(
            {"page_index": page_index, "page": page_index + 1, "bbox": [0.0, top, width, bottom]}
        )
    return fragments


def extract_text(page, bbox: list[float]) -> str:  # type: ignore[no-untyped-def]
    text = page.crop(tuple(bbox), strict=False).extract_text(x_tolerance=2, y_tolerance=3)
    # pdfplumber normalizes the PDF's non-breaking space in its protected-email
    # placeholder. Restore the source character instead of silently changing it.
    return (text or "").replace("[email protected]", "[email\u00a0protected]").strip()


def split_sections(raw_text: str) -> tuple[str, str, str]:
    explanation_match = re.search(r"(?im)^\s*Explanation\s*$", raw_text)
    if not explanation_match:
        return raw_text.strip(), "", ""
    question_text = raw_text[: explanation_match.start()].strip()
    remainder = raw_text[explanation_match.end() :]
    community_match = re.search(r"(?im)^\s*Community Discussion\s*$", remainder)
    if not community_match:
        return question_text, remainder.strip(), ""
    explanation = remainder[: community_match.start()].strip()
    discussion = remainder[community_match.end() :].strip()
    return question_text, explanation, discussion


def parse_explicit_answer(explanation: str) -> tuple[str, list[str]]:
    match = re.search(r"(?im)^\s*Correct Answer:\s*([^\n]*)$", explanation)
    if not match:
        return "", []
    same_line = match.group(1).strip()
    following = explanation[match.end() :]
    if same_line:
        raw = same_line
    else:
        lines = [line.strip() for line in following.splitlines() if line.strip()]
        raw = (
            ""
            if not lines or re.match(r"^(References:|Community Discussion)$", lines[0], re.I)
            else lines[0]
        )
    compact = re.sub(r"[^A-Za-z]", "", raw).upper()
    keys = (
        list(compact)
        if compact and len(compact) <= 10 and set(compact) <= set("ABCDEFGHIJ")
        else []
    )
    return raw, keys


def parse_options(question_section: str) -> tuple[str, list[dict[str, Any]], list[str]]:
    matches = list(OPTION_RE.finditer(question_section))
    options: list[dict[str, Any]] = []
    tagged: list[str] = []
    for position, match in enumerate(matches, start=1):
        key = match.group(1)
        block = match.group(0).strip()
        if re.search(r"\(Correct Answer\)", block, re.I):
            tagged.append(key)
        without_prefix = re.sub(rf"(?s)^\s*{re.escape(key)}\)\s*", "", block, count=1)
        cleaned = CORRECT_RE.sub(" ", without_prefix).strip()
        options.append({"key": key, "position": position, "text": cleaned})
    if matches:
        prompt = question_section[: matches[0].start()].strip()
    else:
        prompt = question_section.strip()
    prompt = re.sub(r"(?im)^\s*Question\s*#\s*\d+\s*$", "", prompt, count=1).strip()
    return prompt, options, tagged


def classify(question_section: str, options: list[dict[str, Any]], answer_keys: list[str]) -> str:
    upper = question_section.upper()
    if re.search(r"\bDRAG\s+DROP\s*-?", upper):
        return "drag_drop"
    if re.search(r"\bHOTSPOT\s*-?", upper):
        return "hotspot"
    if (
        len(options) == 2
        and options[0]["text"].strip() == "Yes"
        and options[1]["text"].strip() == "No"
    ):
        return "yes_no"
    return "multiple_choice" if len(answer_keys) > 1 else "single_choice"


def parse_references(explanation: str) -> list[dict[str, Any]]:
    match = re.search(r"(?im)^\s*References:\s*$", explanation)
    if not match:
        return []
    raw = explanation[match.end() :].strip()
    if not raw:
        return []
    collapsed = re.sub(r"\s*\n\s*", "", raw)
    urls = re.findall(r"https?://[^\s]+", collapsed)
    return [{"position": 1, "raw_text": raw, "url": urls[0] if len(urls) == 1 else None}]


def _dedupe_boxes(
    curves: list[dict[str, Any]], bbox: list[float], min_top: float
) -> list[list[float]]:
    candidates: list[list[float]] = []
    for curve in curves:
        width = float(curve["x1"] - curve["x0"])
        height = float(curve["bottom"] - curve["top"])
        if width < 400 or height < 18 or not (55 <= curve["x0"] <= 85):
            continue
        if curve["top"] < max(bbox[1], min_top) - 3 or curve["bottom"] > bbox[3] + 3:
            continue
        candidate = [
            float(curve["x0"]),
            float(curve["top"]),
            float(curve["x1"]),
            float(curve["bottom"]),
        ]
        existing = next(
            (
                item
                for item in candidates
                if abs(item[1] - candidate[1]) < 4 and abs(item[3] - candidate[3]) < 4
            ),
            None,
        )
        if existing:
            existing[0] = min(existing[0], candidate[0])
            existing[1] = min(existing[1], candidate[1])
            existing[2] = max(existing[2], candidate[2])
            existing[3] = max(existing[3], candidate[3])
        else:
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: item[1])


def parse_comments(
    pdf, fragments: list[dict[str, Any]], discussion_raw: str
) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    comments: list[dict[str, Any]] = []
    in_comments = False
    for fragment in fragments:
        page = pdf.pages[fragment["page_index"]]
        bbox = fragment["bbox"]
        cropped = page.crop(tuple(bbox), strict=False)
        headings = cropped.search("Community Discussion")
        minimum = bbox[1]
        if headings:
            in_comments = True
            minimum = max(item["bottom"] for item in headings)
        if not in_comments:
            continue
        for box in _dedupe_boxes(page.curves, bbox, minimum):
            inner = (box[0] + 6, box[1] + 2, box[2] - 6, box[3] - 2)
            text = (
                page.crop(inner, strict=False).extract_text(x_tolerance=2, y_tolerance=3) or ""
            ).strip()
            if not text:
                continue
            selected_match = re.search(r"Selected Answer:\s*([A-Z]+)", text, re.I)
            selected = selected_match.group(1).upper() if selected_match else None
            current = {
                "position": len(comments) + 1,
                "raw_text": text,
                "selected_answer": selected,
                "source_pages": [fragment["page"]],
                "source_bboxes": [[round(value, 3) for value in box]],
            }
            if (
                comments
                and comments[-1]["source_bboxes"][-1][3] >= 780
                and box[1] <= HEADER_BOTTOM + 2
                and comments[-1]["source_pages"][-1] + 1 == fragment["page"]
            ):
                comments[-1]["raw_text"] += "\n" + text
                comments[-1]["source_pages"].append(fragment["page"])
                comments[-1]["source_bboxes"].append([round(value, 3) for value in box])
            else:
                comments.append(current)
    for position, item in enumerate(comments, start=1):
        item["position"] = position
    if discussion_raw and not comments:
        comments.append(
            {
                "position": 1,
                "raw_text": discussion_raw,
                "selected_answer": None,
                "source_pages": [fragment["page"] for fragment in fragments],
                "source_bboxes": [],
            }
        )
    return comments


class Renderer:
    def __init__(self, pdf_path: Path, media_dir: Path, scale: float) -> None:
        self.document = pdfium.PdfDocument(str(pdf_path))
        self.media_dir = media_dir
        self.scale = scale
        self.cached_page = -1
        self.cached_image: Image.Image | None = None

    def page_image(self, page_index: int) -> Image.Image:
        if self.cached_page != page_index:
            self.cached_image = (
                self.document[page_index].render(scale=self.scale).to_pil().convert("RGB")
            )
            self.cached_page = page_index
        assert self.cached_image is not None
        return self.cached_image

    def save_crop(
        self, page_index: int, page_size: tuple[float, float], bbox: list[float]
    ) -> tuple[str, str, int, int]:
        image = self.page_image(page_index)
        x_ratio = image.width / page_size[0]
        y_ratio = image.height / page_size[1]
        pixel_bbox = (
            max(0, round(bbox[0] * x_ratio)),
            max(0, round(bbox[1] * y_ratio)),
            min(image.width, round(bbox[2] * x_ratio)),
            min(image.height, round(bbox[3] * y_ratio)),
        )
        crop = image.crop(pixel_bbox)
        from io import BytesIO

        buffer = BytesIO()
        # Method 1 keeps the crop pixel-perfect while avoiding the very slow
        # exhaustive encoder search used by method 6 on full-page fragments.
        crop.save(buffer, format="WEBP", lossless=True, method=1)
        data = buffer.getvalue()
        digest = sha256_bytes(data)
        relative = Path(digest[:2]) / f"{digest}.webp"
        target = self.media_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
        return relative.as_posix(), digest, crop.width, crop.height


def _image_role(
    page, image_bbox: list[float], fragment_bbox: list[float], state: str
) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    crop = page.crop(tuple(fragment_bbox), strict=False)
    explanation = crop.search("Explanation")
    community = crop.search("Community Discussion")
    exp_top = min((item["top"] for item in explanation), default=None)
    com_top = min((item["top"] for item in community), default=None)
    image_top = image_bbox[1]
    if state == "question" and exp_top is not None and image_top >= exp_top:
        state = "answer"
    if state == "answer" and com_top is not None and image_top >= com_top:
        state = "comments"
    role = {"question": "question_asset", "answer": "answer_asset", "comments": "comment_asset"}[
        state
    ]
    next_state = state
    if community:
        next_state = "comments"
    elif explanation:
        next_state = "answer"
    return role, next_state


def render_media(
    renderer: Renderer,
    pdf,
    fragments: list[dict[str, Any]],
    page_sizes: list[tuple[float, float]],
) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    media: list[dict[str, Any]] = []
    state = "question"
    for fragment in fragments:
        page = pdf.pages[fragment["page_index"]]
        bbox = fragment["bbox"]
        path, digest, width, height = renderer.save_crop(
            fragment["page_index"], page_sizes[fragment["page_index"]], bbox
        )
        media.append(
            {
                "position": len(media) + 1,
                "role": "source_fragment",
                "sha256": digest,
                "relative_path": path,
                "mime_type": "image/webp",
                "width": width,
                "height": height,
                "source_page": fragment["page"],
                "source_bbox": [round(value, 3) for value in bbox],
            }
        )
        seen_images: set[tuple[float, float, float, float]] = set()
        for image in page.images:
            image_bbox = [
                float(image["x0"]),
                float(image["top"]),
                float(image["x1"]),
                float(image["bottom"]),
            ]
            key = tuple(round(value, 2) for value in image_bbox)
            if key in seen_images:
                continue
            seen_images.add(key)
            if (
                image_bbox[0] < 55
                or image_bbox[2] - image_bbox[0] < 50
                or image_bbox[3] - image_bbox[1] < 20
            ):
                continue
            if image_bbox[1] < bbox[1] - 1 or image_bbox[3] > bbox[3] + 1:
                continue
            role, state_after = _image_role(page, image_bbox, bbox, state)
            path, digest, width, height = renderer.save_crop(
                fragment["page_index"], page_sizes[fragment["page_index"]], image_bbox
            )
            media.append(
                {
                    "position": len(media) + 1,
                    "role": role,
                    "sha256": digest,
                    "relative_path": path,
                    "mime_type": "image/webp",
                    "width": width,
                    "height": height,
                    "source_page": fragment["page"],
                    "source_bbox": [round(value, 3) for value in image_bbox],
                }
            )
            state = state_after
        crop = page.crop(tuple(bbox), strict=False)
        if crop.search("Community Discussion"):
            state = "comments"
        elif crop.search("Explanation"):
            state = "answer"
    return media


def extract(pdf_path: Path, canonical_dir: Path, media_dir: Path, scale: float) -> None:
    canonical_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_file(pdf_path)
    reader = PdfReader(str(pdf_path))
    anchors = load_anchors(reader)
    with pdfplumber.open(str(pdf_path)) as pdf:
        page_sizes = [(float(page.width), float(page.height)) for page in pdf.pages]
        renderer = Renderer(pdf_path, media_dir, scale)
        records: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []
        for number in range(1, QUESTION_COUNT + 1):
            fragments = fragment_bboxes(anchors, number, page_sizes)
            fragment_texts = [
                extract_text(pdf.pages[item["page_index"]], item["bbox"]) for item in fragments
            ]
            raw_text = "\n".join(text for text in fragment_texts if text).strip()
            question_section, explanation_raw, discussion_raw = split_sections(raw_text)
            prompt, options, tagged_keys = parse_options(question_section)
            explicit_raw, explicit_keys = parse_explicit_answer(explanation_raw)
            answer_keys = explicit_keys or tagged_keys
            question_type = classify(question_section, options, answer_keys)
            media = render_media(renderer, pdf, fragments, page_sizes)
            interaction = {
                "kind": question_type,
                "grading_mode": "automatic" if answer_keys and options else "reveal_only",
                "response_schema": (
                    {"choice_keys": "string[]"}
                    if answer_keys and options
                    else {"reveal": "boolean"}
                ),
            }
            record: dict[str, Any] = {
                "schema_version": "1.0",
                "id": f"mb230-q{number:04d}",
                "exam_id": "mb-230",
                "pdf_order": number,
                "source_question_number": number,
                "question_type": question_type,
                "language": "en",
                "prompt_text": prompt,
                "raw_text": raw_text,
                "options": options,
                "source_answer": {
                    "raw_text": explicit_raw,
                    "option_keys": answer_keys,
                    "status": "as_published",
                },
                "verified_answer": None,
                "explanation_raw": explanation_raw,
                "references": parse_references(explanation_raw),
                "community_discussion_raw": discussion_raw,
                "community_comments": parse_comments(pdf, fragments, discussion_raw),
                "interaction": interaction,
                "media": media,
                "source_pages": {"start": fragments[0]["page"], "end": fragments[-1]["page"]},
                "source_fragments": [
                    {
                        "ordinal": index,
                        "page": item["page"],
                        "bbox": [round(value, 3) for value in item["bbox"]],
                        "raw_text": fragment_texts[index - 1],
                    }
                    for index, item in enumerate(fragments, start=1)
                ],
                "review_status": "auto_extracted",
            }
            record["content_sha256"] = canonical_hash(record)
            records.append(record)
            if not re.search(rf"(?im)^\s*Question\s*#\s*{number}\s*$", question_section):
                issues.append({"question": number, "issue": "question_marker_missing"})
            if "Community Discussion" not in raw_text:
                issues.append({"question": number, "issue": "community_heading_missing"})
            if question_type in {"drag_drop", "hotspot"} and not any(
                item["role"] == "question_asset" for item in media
            ):
                issues.append({"question": number, "issue": "interactive_question_asset_missing"})
            if number % 25 == 0:
                print(f"Extracted {number}/{QUESTION_COUNT}", flush=True)

    questions_path = canonical_dir / "questions.jsonl"
    with questions_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    questions_hash = sha256_file(questions_path)
    dataset_hash = sha256_bytes(f"{source_hash}:{questions_hash}:1.0".encode())
    type_counts = dict(sorted(Counter(record["question_type"] for record in records).items()))
    manifest = {
        "schema_version": "1.0",
        "dataset_sha256": dataset_hash,
        "questions_sha256": questions_hash,
        "question_count": len(records),
        "exam": {
            "slug": "mb-230",
            "title": "Microsoft MB-230 Practice Questions",
            "description": "Questions preserved in the order and wording of the supplied PDF.",
        },
        "source": {
            "filename": pdf_path.name,
            "sha256": source_hash,
            "page_count": len(reader.pages),
        },
        "type_counts": type_counts,
        "media_count": sum(len(record["media"]) for record in records),
        "issues_count": len(issues),
    }
    (canonical_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (canonical_dir / "qa-report.json").write_text(
        json.dumps({"manifest": manifest, "issues": issues}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract the MB-230 PDF into canonical API data")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--canonical-dir", required=True, type=Path)
    parser.add_argument("--media-dir", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.6)
    args = parser.parse_args()
    extract(args.pdf, args.canonical_dir, args.media_dir, args.scale)


if __name__ == "__main__":
    main()
