import streamlit as st
from utils.compress import compress_pdf, QUALITY_PRESETS

st.set_page_config(page_title="PDF 工具箱 v3", page_icon="📄", layout="centered")

st.title("📄 PDF 工具箱 v3")

# --- 側邊欄工具選單（之後可以加更多工具）---
tool = st.sidebar.radio("選擇工具", ["🗜️ 壓縮 PDF"])

# ── 壓縮工具 ──────────────────────────────────────────────────────────────────
if tool == "🗜️ 壓縮 PDF":
    st.subheader("🗜️ 壓縮 PDF")
    st.caption("使用 Ghostscript 深度壓縮，保留可讀品質")

    uploaded = st.file_uploader("上傳 PDF", type="pdf")

    quality = st.selectbox("壓縮品質", list(QUALITY_PRESETS.keys()), index=1)

    if uploaded:
        original_bytes = uploaded.read()
        original_size  = len(original_bytes)
        st.info(f"原始大小：{original_size / 1024:.1f} KB")

        if st.button("開始壓縮", type="primary"):
            with st.spinner("壓縮中，請稍候..."):
                try:
                    compressed, did_shrink = compress_pdf(original_bytes, quality)
                    compressed_size = len(compressed)
                    ratio = (1 - compressed_size / original_size) * 100

                    if did_shrink:
                        st.success(
                            f"壓縮完成！{original_size/1024:.1f} KB → "
                            f"{compressed_size/1024:.1f} KB（縮小 {ratio:.1f}%）"
                        )
                    else:
                        st.warning("此 PDF 已高度壓縮，無法進一步縮小，回傳原始檔案。")

                    st.download_button(
                        label="⬇️ 下載壓縮後 PDF",
                        data=compressed,
                        file_name=f"compressed_{uploaded.name}",
                        mime="application/pdf",
                    )
                except EnvironmentError as e:
                    st.error(str(e))
                except RuntimeError as e:
                    st.error(str(e))
