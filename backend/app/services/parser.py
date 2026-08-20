import base64
import io
import re
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import pymupdf as fitz
import pytesseract
from PIL import Image, ImageOps, ImageSequence
from pytesseract import Output

ProcessingMode = Literal["smart", "native", "visual", "docling"]
VisualReader = Literal["ocr", "vision"]


@dataclass
class ParsedDocument:
    canonical: dict[str, Any]
    model_text: str
    visual_pages: list[dict[str, Any]]


def _block(block_id: str, text: str, bbox: tuple[float, float, float, float] | None = None, source: str = "embedded") -> dict[str, Any]:
    return {"id": block_id, "type": "text", "text": text, "bbox": ({"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3], "coordinate_system": "top_left_normalized"} if bbox else None), "confidence": None, "source": source}


@lru_cache(maxsize=1)
def _docling_converter():
    """Keep model state warm for the lifetime of each worker process."""
    from docling.document_converter import DocumentConverter
    return DocumentConverter()


def _docling_markdown(data: bytes, filename: str) -> str | None:
    suffix = Path(filename).suffix[:12] or ".pdf"
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(data)
            path = handle.name
        result = _docling_converter().convert(path)
        return result.document.export_to_markdown()
    except Exception:
        return None
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


def _schema_requests_tables(schema: dict[str, Any] | None, instructions: str) -> bool:
    terms: list[str] = [instructions]

    def walk(node: Any, key: str = "") -> None:
        if not isinstance(node, dict):
            return
        terms.extend((key, str(node.get("title", "")), str(node.get("description", ""))))
        for child_key, child in node.get("properties", {}).items():
            walk(child, child_key)
        if isinstance(node.get("items"), dict):
            walk(node["items"], key)

    walk(schema or {})
    haystack = " ".join(terms).lower()
    return bool(re.search(r"\b(table|tabular|line[ _-]?items?|rows?|columns?|transactions?|ledger|schedule)\b", haystack))


def _intersection_ratio(first: fitz.Rect, second: fitz.Rect) -> float:
    overlap = first & second
    if overlap.is_empty or first.get_area() <= 0:
        return 0.0
    return overlap.get_area() / first.get_area()


def _vector_selection_marks(page: fitz.Page) -> list[dict[str, Any]]:
    """Interpret drawn X marks inside vector checkbox rectangles."""
    drawings = page.get_drawings()
    boxes: list[fitz.Rect] = []
    for drawing in drawings:
        for item in drawing.get("items", []):
            if item[0] != "re":
                continue
            rect = fitz.Rect(item[1])
            if 5 <= rect.width <= 30 and 5 <= rect.height <= 30:
                boxes.append(rect)

    words = page.get_text("words")
    selections: list[dict[str, Any]] = []
    for drawing in drawings:
        line_items = [item for item in drawing.get("items", []) if item[0] == "l"]
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        if not (2 <= rect.width <= 24 and 2 <= rect.height <= 24 and len(line_items) >= 2):
            continue
        slopes = []
        for _, start, end in line_items:
            dx, dy = end.x - start.x, end.y - start.y
            if abs(dx) >= 2 and abs(dy) >= 2:
                slopes.append(dx * dy)
        if not (any(value > 0 for value in slopes) and any(value < 0 for value in slopes)):
            continue
        containing_box = next((box for box in boxes if (box + (-1, -1, 1, 1)).contains(rect)), None)
        if containing_box is None:
            continue

        center_y = (rect.y0 + rect.y1) / 2
        label_candidates = [word for word in words
                            if word[2] <= containing_box.x0 + 2
                            and 0 <= containing_box.x0 - word[2] <= 45
                            and abs(((word[1] + word[3]) / 2) - center_y) <= 7]
        label_word = min(label_candidates, key=lambda word: containing_box.x0 - word[2], default=None)
        label = str(label_word[4]).strip() if label_word else "checked"
        label_x = label_word[0] if label_word else containing_box.x0
        row_words = [word for word in words
                     if word[2] < label_x - 8
                     and abs(((word[1] + word[3]) / 2) - center_y) <= 7
                     and str(word[4]).strip().lower() not in {"yes", "no"}]
        row_words.sort(key=lambda word: word[0])
        question = " ".join(str(word[4]).strip() for word in row_words).strip(" •")
        text = f"Checkbox selection: {question} => {label}" if question else f"Checkbox selection: {label}"
        selections.append({"text": text, "label": label, "question": question, "rect": containing_box})
    return selections


def _page_inspection(page: fitz.Page, *, check_tables: bool) -> dict[str, Any]:
    words = page.get_text("words")
    drawings = page.get_drawings()
    bbox_log = page.get_bboxlog()
    annotations = list(page.annots() or [])
    widgets = list(page.widgets() or [])
    vector_selections = _vector_selection_marks(page)
    image_area = 0.0
    for image in page.get_image_info(xrefs=True):
        bbox = fitz.Rect(image.get("bbox", (0, 0, 0, 0)))
        image_area += max(0.0, bbox.get_area())
    page_area = max(1.0, page.rect.get_area())
    image_coverage = min(1.0, image_area / page_area)

    annotation_types = {str(annotation.type[1]).lower() for annotation in annotations}
    annotation_visual = bool(annotation_types & {"ink", "freeText".lower(), "stamp", "fileattachment"})

    covered_text = False
    late_vector_overlay = False
    for drawing in drawings:
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        seqno = int(drawing.get("seqno", len(bbox_log)))
        fill = drawing.get("fill")
        opaque_white = bool(fill and len(fill) >= 3 and min(fill[:3]) >= 0.94 and float(drawing.get("fill_opacity") or 0) >= 0.9)
        if opaque_white and rect.get_area() >= 300:
            for kind, raw_bbox in bbox_log[:max(0, seqno)]:
                text_rect = fitz.Rect(raw_bbox)
                if kind == "fill-text" and _intersection_ratio(text_rect, rect) >= 0.25:
                    covered_text = True
                    break
        if seqno >= int(len(bbox_log) * 0.75) and drawing.get("type") == "s" and rect.width >= 20 and rect.height >= 5:
            late_vector_overlay = True

    complex_table = False
    if check_tables:
        try:
            complex_table = any(table.row_count >= 3 and table.col_count >= 2 for table in page.find_tables().tables)
        except (AttributeError, RuntimeError, ValueError):
            complex_table = False

    reasons: list[str] = []
    if covered_text: reasons.append("opaque overlay covers earlier text")
    if annotation_visual: reasons.append("visual annotation detected")
    if late_vector_overlay: reasons.append("late vector drawing detected")
    if image_coverage >= 0.55 and len(words) < 20: reasons.append("scanned or image-based page")
    if len(words) < 8 and drawings: reasons.append("insufficient embedded text")
    if complex_table: reasons.append("complex table requested and detected")
    return {
        "word_count": len(words),
        "widget_count": len(widgets),
        "annotation_types": sorted(annotation_types),
        "image_coverage": round(image_coverage, 3),
        "covered_text": covered_text,
        "late_vector_overlay": late_vector_overlay,
        "complex_table": complex_table,
        "selection_mark_count": len(vector_selections),
        "visual_required": bool(covered_text or annotation_visual or late_vector_overlay or (image_coverage >= 0.55 and len(words) < 20) or (len(words) < 8 and drawings)),
        "reasons": reasons,
    }


def _native_page(page: fitz.Page, page_number: int) -> dict[str, Any]:
    width, height = page.rect.width, page.rect.height
    blocks: list[dict[str, Any]] = []
    for sequence, raw in enumerate(page.get_text("blocks")):
        text = raw[4].strip()
        if text:
            bbox = (raw[0] / width, raw[1] / height, raw[2] / width, raw[3] / height)
            blocks.append(_block(f"p{page_number}_b{sequence + 1}", text, bbox))
    for sequence, widget in enumerate(page.widgets() or []):
        value = widget.field_value
        if value in (None, "", "Off"):
            continue
        label = widget.field_label or widget.field_name or f"Field {sequence + 1}"
        text = f"{label}: {value}"
        rect = widget.rect
        bbox = (rect.x0 / width, rect.y0 / height, rect.x1 / width, rect.y1 / height)
        blocks.append(_block(f"p{page_number}_w{sequence + 1}", text, bbox, "widget"))
    for sequence, selection in enumerate(_vector_selection_marks(page)):
        rect = selection["rect"]
        bbox = (rect.x0 / width, rect.y0 / height, rect.x1 / width, rect.y1 / height)
        block = _block(f"p{page_number}_s{sequence + 1}", selection["text"], bbox, "selection_mark")
        block["confidence"] = 1.0
        blocks.append(block)
    return {"page_number": page_number, "width": width, "height": height, "text": "\n".join(block["text"] for block in blocks), "blocks": blocks}


def _render_page(page: fitz.Page, page_number: int) -> dict[str, Any]:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    encoded = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    return {"page_number": page_number, "image_url": f"data:image/png;base64,{encoded}"}


def _ocr_image(image: Image.Image, page_number: int) -> dict[str, Any]:
    """OCR a Pillow image into line-level text blocks with normalized evidence boxes."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    result = pytesseract.image_to_data(image, lang="eng", config="--psm 3", output_type=Output.DICT)
    lines: dict[tuple[int, int, int, int], list[int]] = {}
    for index, raw_text in enumerate(result["text"]):
        if raw_text.strip():
            key = (result["page_num"][index], result["block_num"][index], result["par_num"][index], result["line_num"][index])
            lines.setdefault(key, []).append(index)

    blocks: list[dict[str, Any]] = []
    width, height = image.size
    for sequence, indexes in enumerate(lines.values(), start=1):
        text = " ".join(result["text"][index].strip() for index in indexes)
        x0 = min(result["left"][index] for index in indexes)
        y0 = min(result["top"][index] for index in indexes)
        x1 = max(result["left"][index] + result["width"][index] for index in indexes)
        y1 = max(result["top"][index] + result["height"][index] for index in indexes)
        confidences = [float(result["conf"][index]) / 100 for index in indexes if float(result["conf"][index]) >= 0]
        block = _block(f"p{page_number}_o{sequence}", text, (x0 / width, y0 / height, x1 / width, y1 / height), "ocr")
        block["confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else None
        blocks.append(block)
    return {"page_number": page_number, "width": width, "height": height,
            "text": "\n".join(block["text"] for block in blocks), "blocks": blocks}


def _ocr_page(page: fitz.Page, page_number: int) -> dict[str, Any]:
    """OCR only the rendered pixels, so covered PDF text cannot leak into extraction."""
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    parsed = _ocr_image(Image.open(io.BytesIO(pixmap.tobytes("png"))), page_number)
    for sequence, selection in enumerate(_vector_selection_marks(page)):
        rect = selection["rect"]
        bbox = (rect.x0 / page.rect.width, rect.y0 / page.rect.height, rect.x1 / page.rect.width, rect.y1 / page.rect.height)
        block = _block(f"p{page_number}_s{sequence + 1}", selection["text"], bbox, "selection_mark")
        block["confidence"] = 1.0
        parsed["blocks"].append(block)
    parsed["width"], parsed["height"] = page.rect.width, page.rect.height
    parsed["text"] = "\n".join(block["text"] for block in parsed["blocks"])
    return parsed


def _direct_text_document(data: bytes, mime_type: str, filename: str, *, mode: ProcessingMode) -> ParsedDocument:
    """Prepare plain text and Markdown directly without invoking Docling."""
    text = data.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    for sequence, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
        content = paragraph.strip()
        if content:
            blocks.append(_block(f"p1_b{sequence}", content, None, "native_text"))
    page = {"page_number": 1, "width": None, "height": None, "text": text, "blocks": blocks}
    parser_name = "native-markdown" if filename.lower().endswith(".md") or mime_type == "text/markdown" else "native-text"
    metadata = {"parser": parser_name, "requested_mode": mode, "visual_reader": None, "route": "native",
                "pages": [{"page_number": 1, "route": "native", "reader": None, "reasons": []}]}
    canonical = {"version": "1.1", "page_count": 1, "mime_type": mime_type, "title": filename, "text": text,
                 "markdown": text, "pages": [page], "tables": [], "metadata": metadata}
    return ParsedDocument(canonical, text, [])


def _image_document(data: bytes, mime_type: str, filename: str, *, visual_reader: VisualReader,
                    mode: ProcessingMode, for_extraction: bool) -> ParsedDocument:
    """OCR every image frame; optionally include rendered images for Vision extraction."""
    source = Image.open(io.BytesIO(data))
    pages: list[dict[str, Any]] = []
    visual_pages: list[dict[str, Any]] = []
    for page_number, frame in enumerate(ImageSequence.Iterator(source), start=1):
        image = ImageOps.exif_transpose(frame.copy()).convert("RGB")
        pages.append(_ocr_image(image, page_number))
        if for_extraction and visual_reader == "vision":
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            visual_pages.append({"page_number": page_number, "image_url": f"data:image/png;base64,{encoded}"})
    full_text = "\n\n".join(f"[Page {page['page_number']}]\n{page['text']}" for page in pages)
    reader = "ocr+vision" if visual_pages else "ocr"
    metadata = {"parser": f"tesseract-{reader}", "requested_mode": mode, "visual_reader": visual_reader,
                "route": "visual" if visual_pages else "ocr",
                "pages": [{"page_number": page["page_number"], "route": "visual" if visual_pages else "ocr",
                           "reader": reader, "reasons": ["image document"]} for page in pages]}
    canonical = {"version": "1.1", "page_count": len(pages), "mime_type": mime_type, "title": filename,
                 "text": full_text, "markdown": full_text, "pages": pages, "tables": [], "metadata": metadata}
    return ParsedDocument(canonical, full_text, visual_pages)


def _rasterized_pdf(pdf: fitz.Document) -> bytes:
    raster = fitz.open()
    for page in pdf:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        output_page = raster.new_page(width=page.rect.width, height=page.rect.height)
        output_page.insert_image(output_page.rect, stream=pixmap.tobytes("png"))
    result = raster.tobytes(deflate=True)
    raster.close()
    return result


def prepare_document(data: bytes, mime_type: str, filename: str, *, mode: ProcessingMode = "smart",
                     visual_reader: VisualReader = "vision", schema: dict[str, Any] | None = None,
                     instructions: str = "", for_extraction: bool = True) -> ParsedDocument:
    is_pdf = mime_type == "application/pdf" or filename.lower().endswith(".pdf")
    if not is_pdf:
        suffix = Path(filename).suffix.lower()
        if mime_type in {"text/plain", "text/markdown"} or suffix in {".txt", ".md"}:
            return _direct_text_document(data, mime_type, filename, mode=mode)
        if mime_type.startswith("image/"):
            return _image_document(data, mime_type, filename, visual_reader=visual_reader, mode=mode,
                                   for_extraction=for_extraction)
        markdown = _docling_markdown(data, filename)
        text = markdown or data.decode("utf-8", errors="replace")
        if filename.lower().endswith((".html", ".htm")):
            text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        pages = [{"page_number": 1, "width": None, "height": None, "text": text, "blocks": [_block("p1_b1", text, None, "derived")] if text else []}]
        visual_pages = []
        full_text = "\n\n".join(f"[Page {page['page_number']}]\n{page['text']}" for page in pages)
        metadata = {"parser": "docling" if markdown else "derived", "requested_mode": mode, "visual_reader": visual_reader,
                    "route": "docling" if markdown else "native", "pages": [{"page_number": 1, "route": "visual" if visual_pages else "native", "reader": visual_reader if visual_pages else None, "reasons": []}]}
        canonical = {"version": "1.1", "page_count": len(pages), "mime_type": mime_type, "title": filename, "text": full_text, "markdown": markdown or full_text, "pages": pages, "tables": [], "metadata": metadata}
        return ParsedDocument(canonical, markdown or full_text, visual_pages)

    pdf = fitz.open(stream=data, filetype="pdf")
    table_intent = _schema_requests_tables(schema, instructions)
    inspections = [_page_inspection(page, check_tables=table_intent) for page in pdf]
    docling_required = mode == "docling" or (mode == "smart" and any(item["complex_table"] for item in inspections))
    visual_document = any(item["visual_required"] for item in inspections)

    if docling_required:
        source = _rasterized_pdf(pdf) if visual_document else data
        markdown = _docling_markdown(source, filename) or ""
        if markdown:
            route = "docling-visual" if visual_document else "docling"
            page_routes = [{"page_number": index + 1, "route": route, "reader": "docling", "reasons": item["reasons"]} for index, item in enumerate(inspections)]
        else:
            docling_required = False
            page_routes = [{"page_number": index + 1, "route": "visual", "reader": visual_reader, "reasons": [*item["reasons"], "Docling unavailable; visible-page fallback used"]} for index, item in enumerate(inspections)]
    else:
        markdown = ""
        page_routes = []
        for index, item in enumerate(inspections):
            route = "visual" if mode == "visual" or (mode == "smart" and item["visual_required"]) else "native"
            page_routes.append({"page_number": index + 1, "route": route, "reader": visual_reader if route == "visual" else None, "reasons": item["reasons"]})

    pages = [_native_page(page, index + 1) for index, page in enumerate(pdf)]
    visual_page_numbers = {item["page_number"] for item in page_routes if item["route"] == "visual"}
    if visual_reader == "ocr" and not docling_required:
        for number in sorted(visual_page_numbers):
            pages[number - 1] = _ocr_page(pdf[number - 1], number)
        visual_pages = []
    else:
        visual_pages = [_render_page(pdf[number - 1], number) for number in sorted(visual_page_numbers)] if for_extraction else []
    full_text = "\n\n".join(f"[Page {page['page_number']}]\n{page['text']}" for page in pages)
    native_page_numbers = {item["page_number"] for item in page_routes if item["route"] == "native"}
    text_page_numbers = native_page_numbers | (visual_page_numbers if visual_reader == "ocr" else set())
    model_text = markdown if docling_required else "\n\n".join(f"[Page {page['page_number']}]\n{page['text']}" for page in pages if page["page_number"] in text_page_numbers)
    route_name = "docling" if docling_required else "visual" if visual_page_numbers == set(range(1, len(pages) + 1)) else "native" if not visual_page_numbers else "hybrid"
    metadata = {"parser": "docling" if docling_required else f"smart-hybrid-{visual_reader}" if mode == "smart" else f"pymupdf-{mode}-{visual_reader}",
                "requested_mode": mode, "visual_reader": visual_reader, "route": route_name, "table_intent": table_intent,
                "pages": page_routes, "inspection": inspections}
    canonical = {"version": "1.1", "page_count": len(pages), "mime_type": mime_type, "title": filename, "text": full_text, "markdown": markdown or full_text, "pages": pages, "tables": [], "metadata": metadata}
    pdf.close()
    return ParsedDocument(canonical, model_text, visual_pages)


def parse_document(data: bytes, mime_type: str, filename: str) -> dict[str, Any]:
    """Compatibility wrapper for callers that only need the stored canonical form."""
    return prepare_document(data, mime_type, filename, mode="native", for_extraction=False).canonical
