"""Write eon-whitepaper-share.pdf: a small copy of the paper for sending.

Starts from the lossless eon-whitepaper.pdf every time and changes only how
things are stored, never what is drawn:

1. Illustrations are re-encoded as JPEG (quality 88, no chroma subsampling).
   Any placed above 450 dpi is first resampled to 450 dpi, which is past what
   a screen at 200% zoom or a printer resolves.
2. The figures each embed their own DejaVu Sans subset (about 60 copies).
   Subsets of the same face are merged into one font, and every figure's
   CID-to-glyph map is rewritten to point into it.
3. Streams are recompressed into object streams and the file is linearised.

Needs pikepdf, PyMuPDF, Pillow, fontTools and matplotlib (for the full DejaVu
files). mozjpeg-lossless-optimization is used when installed. Run with
--check to render every page of both files and report the worst difference.
"""

from __future__ import annotations

import io
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import pikepdf
import pymupdf
from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image
from pikepdf import Name

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "eon-whitepaper.pdf"
TARGET = HERE / "eon-whitepaper-share.pdf"
MAX_DPI = 450
JPEG_QUALITY = 88
MIN_IMAGE_BYTES = 200_000
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def placed_dpi() -> dict[int, float]:
    """Highest dpi at which each image xref is drawn anywhere in the source."""
    dpi: dict[int, float] = defaultdict(float)
    with pymupdf.open(SOURCE) as doc:
        for page in doc:
            for info in page.get_image_info(xrefs=True):
                width_in = (info["bbox"][2] - info["bbox"][0]) / 72
                if info["xref"] and width_in > 0:
                    dpi[info["xref"]] = max(dpi[info["xref"]], info["width"] / width_in)
    return dpi


def encode_jpeg(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True, progressive=True)
    data = buf.getvalue()
    try:
        import mozjpeg_lossless_optimization

        data = mozjpeg_lossless_optimization.optimize(data)
    except ImportError:
        pass
    return data


def recompress_images(pdf: pikepdf.Pdf) -> None:
    dpi = placed_dpi()
    for obj in pdf.objects:
        if not isinstance(obj, pikepdf.Stream) or obj.get("/Subtype") != Name.Image:
            continue
        if len(obj.read_raw_bytes()) < MIN_IMAGE_BYTES or "/SMask" in obj:
            continue
        image = pikepdf.PdfImage(obj).as_pil_image().convert("RGB")
        shown = dpi.get(obj.objgen[0], 0.0)
        if shown > MAX_DPI:
            scale = MAX_DPI / shown
            size = (round(image.width * scale), round(image.height * scale))
            image = image.resize(size, Image.Resampling.LANCZOS)
        obj.write(encode_jpeg(image), filter=Name.DCTDecode)
        if "/DecodeParms" in obj:
            del obj["/DecodeParms"]
        obj.Width, obj.Height = image.width, image.height
        obj.ColorSpace, obj.BitsPerComponent = Name.DeviceRGB, 8


def merge_dejavu(pdf: pikepdf.Pdf) -> None:
    """Replace every DejaVu subset of a face with one shared subset."""
    faces: dict[str, list[tuple[pikepdf.Dictionary, dict[int, str]]]] = defaultdict(list)
    for obj in pdf.objects:
        if not isinstance(obj, pikepdf.Dictionary) or obj.get("/Subtype") != Name.CIDFontType2:
            continue
        face = str(obj.BaseFont).split("+")[-1]
        if not face.startswith("DejaVu") or not isinstance(obj.get("/CIDToGIDMap"), pikepdf.Stream):
            continue
        order = TTFont(io.BytesIO(obj.FontDescriptor.FontFile2.read_bytes())).getGlyphOrder()
        raw = obj.CIDToGIDMap.read_bytes()
        cids = {i: order[(raw[2 * i] << 8) | raw[2 * i + 1]] for i in range(len(raw) // 2)}
        faces[face].append((obj, {c: g for c, g in cids.items() if g != ".notdef"}))

    for face, fonts in faces.items():
        full = FONT_DIR / f"{face}.ttf"
        names = sorted({g for _, cids in fonts for g in cids.values()})
        options = subset.Options()
        options.glyph_names = True
        options.notdef_outline = True
        options.name_IDs = ["*"]
        font = TTFont(full)
        subsetter = subset.Subsetter(options)
        subsetter.populate(glyphs=names)
        subsetter.subset(font)
        gid = {name: i for i, name in enumerate(font.getGlyphOrder())}
        buf = io.BytesIO()
        font.save(buf)
        shared = pikepdf.Stream(pdf, buf.getvalue())
        shared.Length1 = len(buf.getvalue())
        for cidfont, cids in fonts:
            table = bytearray(2 * (max(cids, default=0) + 1))
            for cid, name in cids.items():
                table[2 * cid : 2 * cid + 2] = gid[name].to_bytes(2, "big")
            cidfont.CIDToGIDMap = pikepdf.Stream(pdf, bytes(table))
            cidfont.FontDescriptor.FontFile2 = shared
            if "/CIDSet" in cidfont.FontDescriptor:
                del cidfont.FontDescriptor["/CIDSet"]


def check() -> None:
    import numpy as np

    worst = (99.0, -1)
    with pymupdf.open(SOURCE) as a, pymupdf.open(TARGET) as b:
        assert len(a) == len(b), "page count changed"
        for i in range(len(a)):
            assert a[i].get_text() == b[i].get_text(), f"text changed on page {i + 1}"
            x = np.frombuffer(a[i].get_pixmap(dpi=150).samples, np.uint8).astype(float)
            y = np.frombuffer(b[i].get_pixmap(dpi=150).samples, np.uint8).astype(float)
            mse = ((x - y) ** 2).mean()
            psnr = 99.0 if mse == 0 else 10 * np.log10(255**2 / mse)
            worst = min(worst, (psnr, i + 1))
    print(f"text identical; worst page {worst[1]} at {worst[0]:.1f} dB PSNR (99 = identical)")


def main() -> None:
    with pikepdf.open(SOURCE) as pdf:
        recompress_images(pdf)
        merge_dejavu(pdf)
        pdf.remove_unreferenced_resources()
        pdf.save(
            TARGET,
            compress_streams=True,
            recompress_flate=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            linearize=True,
        )
    print(f"{SOURCE.name} {SOURCE.stat().st_size / 1e6:.1f} MB -> "
          f"{TARGET.name} {TARGET.stat().st_size / 1e6:.2f} MB")
    if "--check" in sys.argv:
        check()


if __name__ == "__main__":
    main()
