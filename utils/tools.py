import io
import zipfile
import pikepdf
import fitz
from PIL import Image


# ── 1. 合併 PDF ───────────────────────────────────────────────────────────────
def merge_pdfs(files_bytes: list[bytes]) -> bytes:
    merged = pikepdf.Pdf.new()
    for fb in files_bytes:
        with pikepdf.open(io.BytesIO(fb)) as pdf:
            merged.pages.extend(pdf.pages)
    buf = io.BytesIO()
    merged.save(buf)
    return buf.getvalue()


# ── 2. 拆分 PDF ───────────────────────────────────────────────────────────────
def split_pdf(input_bytes: bytes) -> list[tuple[str, bytes]]:
    """回傳 [(filename, bytes), ...] 每頁一個檔"""
    results = []
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            single = pikepdf.Pdf.new()
            single.pages.append(page)
            buf = io.BytesIO()
            single.save(buf)
            results.append((f"page_{i+1:03d}_of_{total}.pdf", buf.getvalue()))
    return results


# ── 3. PDF 轉圖片 ─────────────────────────────────────────────────────────────
def pdf_to_images(input_bytes: bytes, dpi: int = 150) -> list[tuple[str, bytes]]:
    """回傳 [(filename, png_bytes), ...] 每頁一張"""
    results = []
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        results.append((f"page_{i+1:03d}.png", img_bytes))
    doc.close()
    return results


# ── 4. 圖片合成 PDF ───────────────────────────────────────────────────────────
def images_to_pdf(files_bytes: list[bytes]) -> bytes:
    images = []
    for fb in files_bytes:
        img = Image.open(io.BytesIO(fb)).convert("RGB")
        images.append(img)
    if not images:
        raise ValueError("沒有可用的圖片")
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


# ── 打包成 zip ────────────────────────────────────────────────────────────────
def pack_zip(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    return buf.getvalue()
