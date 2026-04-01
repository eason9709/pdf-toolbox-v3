import subprocess
import tempfile
import os
import shutil

# Ghostscript preset mapping
QUALITY_PRESETS = {
    "高品質 (150 DPI)":  {"preset": "/ebook",  "dpi": 150},
    "平衡 (96 DPI)":     {"preset": "/ebook",  "dpi": 96},
    "最小化 (72 DPI)":   {"preset": "/screen", "dpi": 72},
}

def _find_gs() -> str:
    """找 ghostscript 執行檔，相容 Linux / Windows"""
    for candidate in ("gs", "gswin64c", "gswin32c"):
        if shutil.which(candidate):
            return candidate
    raise EnvironmentError(
        "找不到 Ghostscript，請確認已安裝（packages.txt 加上 ghostscript）"
    )

def compress_pdf(input_bytes: bytes, quality: str) -> bytes:
    """
    用 Ghostscript 壓縮 PDF。
    回傳壓縮後的 bytes，若壓縮後反而更大則回傳原始 bytes。
    """
    preset = QUALITY_PRESETS[quality]
    gs_bin = _find_gs()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")

        # 寫入暫存
        with open(input_path, "wb") as f:
            f.write(input_bytes)

        cmd = [
            gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={preset['preset']}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            # 圖片 DPI 上限
            f"-dColorImageResolution={preset['dpi']}",
            f"-dGrayImageResolution={preset['dpi']}",
            f"-dMonoImageResolution={preset['dpi']}",
            # 圖片下採樣
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            # 移除不必要資料
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
            output_bytes = f.read()

    # 壓縮後反而更大就退回原始
    if len(output_bytes) >= len(input_bytes):
        return input_bytes, False

    return output_bytes, True
