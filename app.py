import streamlit as st
from utils.compress import compress_pdf, QUALITY_PRESETS
from utils.tools import merge_pdfs, split_pdf, pdf_to_images, images_to_pdf, pack_zip

st.set_page_config(page_title="PDF 工具箱 v3", page_icon="📄", layout="centered")
st.title("📄 PDF 工具箱 v3")

tool = st.sidebar.radio("選擇工具", [
    "🗜️ 壓縮 PDF",
    "🔗 合併 PDF",
    "✂️ 拆分 PDF",
    "🖼️ PDF 轉圖片",
    "📑 圖片合成 PDF",
])

# ── 壓縮 ──────────────────────────────────────────────────────────────────────
if tool == "🗜️ 壓縮 PDF":
    st.subheader("🗜️ 壓縮 PDF")
    st.caption("使用 Ghostscript 深度壓縮，保留可讀品質")

    uploaded = st.file_uploader("上傳 PDF", type="pdf")
    quality  = st.selectbox("壓縮品質", list(QUALITY_PRESETS.keys()), index=1)

    if uploaded and st.button("開始壓縮", type="primary"):
        original_bytes = uploaded.read()
        with st.spinner("壓縮中..."):
            try:
                compressed, did_shrink = compress_pdf(original_bytes, quality)
                ratio = (1 - len(compressed) / len(original_bytes)) * 100
                if did_shrink:
                    st.success(f"{len(original_bytes)/1024:.1f} KB → {len(compressed)/1024:.1f} KB（縮小 {ratio:.1f}%）")
                else:
                    st.warning("此 PDF 已高度壓縮，無法進一步縮小。")
                st.download_button("⬇️ 下載", compressed, f"compressed_{uploaded.name}", "application/pdf")
            except Exception as e:
                st.error(str(e))

# ── 合併 ──────────────────────────────────────────────────────────────────────
elif tool == "🔗 合併 PDF":
    st.subheader("🔗 合併 PDF")
    st.caption("上傳多個 PDF，依照順序合併成一個檔案")

    uploaded = st.file_uploader("上傳 PDF（可多選）", type="pdf", accept_multiple_files=True)

    if uploaded:
        st.info(f"已選 {len(uploaded)} 個檔案，將依上方順序合併")
        if st.button("開始合併", type="primary"):
            with st.spinner("合併中..."):
                try:
                    result = merge_pdfs([f.read() for f in uploaded])
                    st.success(f"合併完成，共 {len(uploaded)} 個檔案")
                    st.download_button("⬇️ 下載合併後 PDF", result, "merged.pdf", "application/pdf")
                except Exception as e:
                    st.error(str(e))

# ── 拆分 ──────────────────────────────────────────────────────────────────────
elif tool == "✂️ 拆分 PDF":
    st.subheader("✂️ 拆分 PDF")
    st.caption("將 PDF 每頁拆成獨立檔案，打包成 ZIP 下載")

    uploaded = st.file_uploader("上傳 PDF", type="pdf")

    if uploaded and st.button("開始拆分", type="primary"):
        with st.spinner("拆分中..."):
            try:
                pages = split_pdf(uploaded.read())
                zip_bytes = pack_zip(pages)
                st.success(f"拆分完成，共 {len(pages)} 頁")
                st.download_button("⬇️ 下載 ZIP", zip_bytes, f"split_{uploaded.name}.zip", "application/zip")
            except Exception as e:
                st.error(str(e))

# ── PDF 轉圖片 ────────────────────────────────────────────────────────────────
elif tool == "🖼️ PDF 轉圖片":
    st.subheader("🖼️ PDF 轉圖片")
    st.caption("每頁轉成 PNG，打包成 ZIP 下載")

    uploaded = st.file_uploader("上傳 PDF", type="pdf")
    dpi = st.select_slider("輸出解析度", options=[72, 96, 120, 150, 200, 300], value=150)

    if uploaded and st.button("開始轉換", type="primary"):
        with st.spinner("轉換中..."):
            try:
                images = pdf_to_images(uploaded.read(), dpi=dpi)
                zip_bytes = pack_zip(images)
                st.success(f"轉換完成，共 {len(images)} 頁")
                st.download_button("⬇️ 下載 ZIP", zip_bytes, f"{uploaded.name}_images.zip", "application/zip")
            except Exception as e:
                st.error(str(e))

# ── 圖片合成 PDF ──────────────────────────────────────────────────────────────
elif tool == "📑 圖片合成 PDF":
    st.subheader("📑 圖片合成 PDF")
    st.caption("上傳多張圖片，依照順序合成一個 PDF")

    uploaded = st.file_uploader("上傳圖片（可多選）", type=["png", "jpg", "jpeg", "bmp", "tiff", "webp"], accept_multiple_files=True)

    if uploaded:
        st.info(f"已選 {len(uploaded)} 張圖片")
        if st.button("開始合成", type="primary"):
            with st.spinner("合成中..."):
                try:
                    result = images_to_pdf([f.read() for f in uploaded])
                    st.success("合成完成")
                    st.download_button("⬇️ 下載 PDF", result, "images_to_pdf.pdf", "application/pdf")
                except Exception as e:
                    st.error(str(e))
