"""Image preprocessing (ported from VGMCP, plan §7.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orca_vision_helper.errors import VisionError, VisionErrorCode
from orca_vision_helper import imaging
from orca_vision_helper.imaging import preprocess


def _make_png(tmp_path: Path, size: tuple[int, int], color=(123, 200, 50)) -> Path:
    from PIL import Image

    p = tmp_path / "shot.png"
    Image.new("RGB", size, color).save(p)
    return p


def test_preprocess_downscales_long_edge(tmp_path):
    src = _make_png(tmp_path, (4000, 1000))
    data, mime, w, h = preprocess(src, max_long_edge=1568, downscale="auto")
    assert w == 1568 and h == 392
    assert mime in ("image/png", "image/jpeg")
    assert len(data) > 0


def test_preprocess_off_keeps_size(tmp_path):
    src = _make_png(tmp_path, (2000, 100))
    _data, _mime, w, h = preprocess(src, max_long_edge=1568, downscale="off")
    assert (w, h) == (2000, 100)


def test_preprocess_small_image_untouched(tmp_path):
    src = _make_png(tmp_path, (800, 600))
    _data, mime, w, h = preprocess(src)
    assert (w, h) == (800, 600)
    assert mime == "image/png"


def test_large_rgb_encoded_as_jpeg(tmp_path):
    src = _make_png(tmp_path, (2000, 1600), color=(10, 20, 30))
    _data, mime, _w, _h = preprocess(src)
    assert mime == "image/jpeg"


def test_rgba_kept_as_png(tmp_path):
    from PIL import Image

    p = tmp_path / "rgba.png"
    Image.new("RGBA", (1200, 1000), (10, 20, 30, 128)).save(p)
    _data, mime, _w, _h = preprocess(p)
    assert mime == "image/png"


@pytest.mark.parametrize("kind", ["directory", "text", "corrupt"])
def test_invalid_image_inputs_map_to_bad_request(tmp_path, kind):
    if kind == "directory":
        path = tmp_path
    else:
        path = tmp_path / "bad.png"
        path.write_bytes(b"not an image" if kind == "text" else b"\x89PNG\r\n")
    with pytest.raises(VisionError) as exc_info:
        preprocess(path)
    assert exc_info.value.code == VisionErrorCode.BAD_REQUEST


def test_file_size_limit_maps_to_bad_request(tmp_path, monkeypatch):
    path = tmp_path / "large.png"
    path.write_bytes(b"12345")
    monkeypatch.setattr(imaging, "MAX_INPUT_BYTES", 4)
    with pytest.raises(VisionError) as exc_info:
        preprocess(path)
    assert exc_info.value.code == VisionErrorCode.BAD_REQUEST
