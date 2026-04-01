import subprocess
import tempfile
import os
import shutil
import io

import pikepdf
import fitz  # pymupdf
from PIL import Image

# Ghostscript preset mapping
QUALITY_PRESETS = {
    "高品質 (150 DPI)":  {"preset": "/ebook",  "dpi": 150, "img_quality": 85},
    "平衡 (96 DPI)":     {"preset": "/ebook",  "dpi": 96,  "img_quality": 75},
    "最小化 (72 DPI)":   {"preset": "/screen", "dpi": 72,  "img_quality": 60},
}

def _find_gs() -> str:
    for candidate in ("gs", "gswin64c", "gswin32c"):
        if shutil.which(candidate):
            return candidate
    raise EnvironmentError(
        "找不到 Ghostscript，請確認已安裝（packages.txt 加上 ghostscript）"
    )

# ── 第一段：pymupdf + Pillow 圖片預處理 ──────────────────────────────────────
def _preprocess_images(input_bytes: bytes, dpi: int, img_quality: int) -> bytes:
    """
    把 PDF 內嵌圖片抽出來，用 Pillow 重壓成 JPEG，再寫回 PDF。
    無法處理的圖片直接跳過，不會讓整個流程爆掉。
    """
    doc = fitz.open(stream=input_bytes, filetype="pdf")

    for page in doc:
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                img_bytes  = base_image["image"]
                colorspace = base_image["colorspace"]  # 1=gray, 3=rgb, 4=cmyk

                img = Image.open(io.BytesIO(img_bytes))

                # CMYK 轉 RGB 避免 JPEG 存檔問題
                if img.mode == "CMYK":
                    img = img.convert("RGB")
                elif img.mode == "P":
                    img = img.convert("RGB")
                elif img.mode == "RGBA":
                    # 白底合併 alpha
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg

                # 縮小解析度
                orig_w, orig_h = img.size
                scale = dpi / 150  # 以 150 為基準縮放
                if scale < 1.0:
                    new_w = max(1, int(orig_w * scale))
                    new_h = max(1, int(orig_h * scale))
                    img = img.resize((new_w, new_h), Image.LANCZOS)

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=img_quality, optimize=True)
                new_bytes = buf.getvalue()

                # 只有真的變小才換
                if len(new_bytes) < len(img_bytes):
                    doc.update_stream(xref, new_bytes)

            except Exception:
                # 單張圖失敗不影響整體
                continue

    result = doc.tobytes(deflate=True, garbage=4)
    doc.close()
    return result


# ── 第二段：Ghostscript 壓縮 ─────────────────────────────────────────────────
def _gs_compress(input_bytes: bytes, preset: str, dpi: int) -> bytes:
    gs_bin = _find_gs()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")

        with open(input_path, "wb") as f:
            f.write(input_bytes)

        cmd = [
            gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={preset}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dMonoImageResolution={dpi}",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            f"-sOutputFile={output_path}",
            input_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ghostscript 錯誤：{result.stderr}")

        with open(output_path, "rb") as f:
            return f.read()


# ── 第三段：pikepdf 清理殘留 ──────────────────────────────────────────────────
def _pikepdf_cleanup(input_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        pdf.save(
            buf,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    return buf.getvalue()


# ── 主入口 ────────────────────────────────────────────────────────────────────
def compress_pdf(input_bytes: bytes, quality: str) -> tuple[bytes, bool]:
    """
    三段式壓縮：圖片預處理 → Ghostscript → pikepdf 清理
    回傳 (壓縮後 bytes, 是否有縮小)
    """
    cfg = QUALITY_PRESETS[quality]
    original_size = len(input_bytes)

    # 第一段
    try:
        stage1 = _preprocess_images(input_bytes, cfg["dpi"], cfg["img_quality"])
    except Exception:
        stage1 = input_bytes  # 失敗就跳過，繼續往下

    # 第二段
    stage2 = _gs_compress(stage1, cfg["preset"], cfg["dpi"])

    # 第三段
    try:
        stage3 = _pikepdf_cleanup(stage2)
    except Exception:
        stage3 = stage2  # 失敗就跳過

    # 取最小的結果
    final = min([input_bytes, stage1, stage2, stage3], key=len)
    did_shrink = len(final) < original_size

    return final, did_shrink
