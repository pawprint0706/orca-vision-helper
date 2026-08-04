"""Image preprocessing before vision API transmission (ported from VGMCP, plan §7.5).

The saved original stays full-resolution; only the transmitted copy is
downscaled to `max_long_edge` (default 1568). This bounds cost/tokens without
hurting layout-level analysis (plan §7.5.2). `downscale="off"` sends as-is.
"""

from __future__ import annotations

import io
import warnings
from pathlib import Path

from .errors import VisionError, VisionErrorCode

# Map Pillow format -> MIME type.
_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
MAX_INPUT_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 80_000_000


def preprocess(
    image_path: Path,
    *,
    max_long_edge: int = 1568,
    downscale: str = "auto",
) -> tuple[bytes, str, int, int]:
    """Return ``(image_bytes, mime_type, width, height)`` ready for transmission.

    PNG is preferred (text/edge fidelity, plan §7.5.1). Very large images are
    re-encoded as JPEG q90 to keep payloads reasonable.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        if not image_path.is_file():
            raise VisionError(
                VisionErrorCode.BAD_REQUEST, f"Image path is not a file: {image_path}"
            )
        input_bytes = image_path.stat().st_size
        if input_bytes > MAX_INPUT_BYTES:
            raise VisionError(
                VisionErrorCode.BAD_REQUEST,
                f"Image file is too large ({input_bytes} bytes; limit {MAX_INPUT_BYTES}).",
            )

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(image_path) as img:
                w, h = img.size
                if w * h > MAX_IMAGE_PIXELS:
                    raise VisionError(
                        VisionErrorCode.BAD_REQUEST,
                        f"Image dimensions are too large ({w}x{h}; limit {MAX_IMAGE_PIXELS} pixels).",
                    )
                img.load()
                # Normalize mode for safe re-encoding.
                if img.mode not in ("RGB", "RGBA", "L"):
                    img = img.convert("RGB")

                long_edge = max(w, h)
                resized = img
                if downscale != "off" and long_edge > max_long_edge:
                    scale = max_long_edge / long_edge
                    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
                    resized = img.resize(new_size, Image.LANCZOS)

                out_w, out_h = resized.size
                buf = io.BytesIO()
                # PNG by default; fall back to JPEG for big RGB images to cap payload.
                use_jpeg = resized.mode == "RGB" and (out_w * out_h) > 1_400_000
                if use_jpeg:
                    resized.save(buf, format="JPEG", quality=90)
                    mime = _MIME["JPEG"]
                else:
                    if resized.mode == "L":
                        resized = resized.convert("RGB")
                    resized.save(buf, format="PNG")
                    mime = _MIME["PNG"]
                return buf.getvalue(), mime, out_w, out_h
    except VisionError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise VisionError(
            VisionErrorCode.BAD_REQUEST, f"Image exceeds safe decompression limits: {image_path}"
        ) from exc
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise VisionError(
            VisionErrorCode.BAD_REQUEST, f"Cannot read image file '{image_path}': {exc}"
        ) from exc
