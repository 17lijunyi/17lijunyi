#!/usr/bin/env python3
"""Embed local, already-generated nail images in a conversation gallery fragment."""

import argparse
import base64
import html
import json
from pathlib import Path
import sys
import uuid


MAX_OUTPUT_BYTES = 1_000_000
MAX_IMAGE_BYTES = 20_000_000
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "gallery-template.html"


def text_value(value, label, default=None):
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def image_data(value, base_dir):
    value = text_value(value, "image path")
    if "://" in value or value.startswith("data:"):
        raise ValueError("Use local image paths, not URLs or data URIs")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    path = path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError(f"Not an image file below 20 MB: {path}")
    payload = path.read_bytes()
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif payload.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif payload.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    elif payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError(f"Unsupported image content; use PNG/JPEG/WebP/GIF: {path}")
    return f"data:{mime};base64," + base64.b64encode(payload).decode("ascii")


def build(manifest_path, output_path):
    manifest_path = manifest_path.resolve(strict=True)
    output_path = output_path.expanduser().resolve()
    if output_path.exists():
        raise FileExistsError(f"Output already exists; choose a new path: {output_path}")
    if output_path.suffix.lower() != ".html":
        raise ValueError("Output must have a .html suffix")
    if manifest_path.stat().st_size > 1_000_000:
        raise ValueError("Manifest is unexpectedly large")
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("Manifest must be a JSON object")
    brand = text_value(spec.get("brand"), "brand", "Muse10")
    title = text_value(spec.get("title"), "title", "作品展示")
    raw_products = spec.get("products")
    if not isinstance(raw_products, list) or not raw_products:
        raise ValueError("products must be a nonempty array")
    products = []
    for index, raw in enumerate(raw_products):
        if not isinstance(raw, dict):
            raise ValueError(f"products[{index}] must be an object")
        paths, labels = raw.get("images"), raw.get("labels")
        if not isinstance(paths, list) or len(paths) < 2:
            raise ValueError(f"products[{index}] needs at least two images for a gallery")
        if not isinstance(labels, list) or len(labels) != len(paths):
            raise ValueError(f"products[{index}] needs one label per image")
        note = raw.get("note", "")
        if not isinstance(note, str):
            raise ValueError(f"products[{index}].note must be text")
        products.append({
            "name": text_value(raw.get("name"), f"products[{index}].name"),
            "note": note,
            "labels": [text_value(label, "image label") for label in labels],
            "images": [image_data(path, manifest_path.parent) for path in paths],
        })
    # JSON lives inside a script element: escape delimiters even though all UI
    # labels later enter the DOM through textContent, not innerHTML.
    data = json.dumps(products, ensure_ascii=False, separators=(",", ":"))
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                          ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        data = data.replace(char, escaped)
    source = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__M10_ROOT_ID__": "muse10-nails-" + uuid.uuid4().hex[:12],
        "__M10_PRODUCT_COUNT__": str(len(products)),
        "__M10_TITLE__": html.escape(title, quote=True),
        "__M10_BRAND__": html.escape(brand, quote=True),
        "__M10_IMAGE_DATA__": data,
    }
    for token, value in replacements.items():
        if token not in source:
            raise ValueError(f"Template is missing {token}")
        source = source.replace(token, value)
    encoded = source.encode("utf-8")
    if len(encoded) >= MAX_OUTPUT_BYTES:
        raise ValueError(
            f"Preview is {len(encoded)} bytes; use smaller preview-image copies "
            f"to keep the fragment below {MAX_OUTPUT_BYTES} bytes. Originals were not changed."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as handle:
        handle.write(encoded)
    return {"path": str(output_path), "bytes": len(encoded), "products": len(products)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.manifest, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
