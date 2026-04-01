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
def _extract_pages(pdf: pikepdf.Pdf, page_indices: list[int]) -> bytes:
    """從 pdf 抽出指定頁碼（0-based）存成 bytes"""
    out = pikepdf.Pdf.new()
    for i in page_indices:
        out.pages.append(pdf.pages[i])
    buf = io.BytesIO()
    out.save(buf)
    return buf.getvalue()


def split_pdf_every_page(input_bytes: bytes) -> list[tuple[str, bytes]]:
    """每頁拆成一個檔"""
    results = []
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        total = len(pdf.pages)
        for i in range(total):
            data = _extract_pages(pdf, [i])
            results.append((f"page_{i+1:03d}_of_{total}.pdf", data))
    return results


def split_pdf_by_interval(input_bytes: bytes, interval: int) -> list[tuple[str, bytes]]:
    """每隔 interval 頁拆一個檔，例如 interval=3 → 1-3, 4-6, ..."""
    results = []
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        total = len(pdf.pages)
        for start in range(0, total, interval):
            end = min(start + interval, total)
            indices = list(range(start, end))
            data = _extract_pages(pdf, indices)
            results.append((f"pages_{start+1:03d}-{end:03d}.pdf", data))
    return results


def split_pdf_by_ranges(input_bytes: bytes, ranges: list[tuple[int, int]]) -> list[tuple[str, bytes]]:
    """
    依自訂範圍拆分，ranges 為 [(start, end), ...] 1-based inclusive。
    例如 [(1,3),(5,8)] → 第1-3頁、第5-8頁各一個檔
    """
    results = []
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        total = len(pdf.pages)
        for s, e in ranges:
            s = max(1, s)
            e = min(total, e)
            if s > e:
                continue
            indices = list(range(s - 1, e))
            data = _extract_pages(pdf, indices)
            results.append((f"pages_{s:03d}-{e:03d}.pdf", data))
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
