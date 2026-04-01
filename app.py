import streamlit as st
from streamlit_sortables import sort_items
from utils.compress import compress_pdf, QUALITY_PRESETS
from utils.tools import (
    merge_pdfs, split_pdf_every_page, split_pdf_by_interval,
    split_pdf_by_ranges, pdf_to_images, images_to_pdf, pack_zip
)

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

# ── 合併（拖拽排序）──────────────────────────────────────────────────────────
elif tool == "🔗 合併 PDF":
    st.subheader("🔗 合併 PDF")
    st.caption("上傳後可拖拽調整順序，再合併")

    uploaded = st.file_uploader("上傳 PDF（可多選）", type="pdf", accept_multiple_files=True)

    if uploaded:
        file_map = {f.name: f for f in uploaded}
        sorted_names = sort_items(list(file_map.keys()), direction="vertical")
        st.caption("👆 拖拽上方列表調整順序")

        if st.button("開始合併", type="primary"):
            with st.spinner("合併中..."):
                try:
                    ordered_bytes = [file_map[n].read() for n in sorted_names]
                    result = merge_pdfs(ordered_bytes)
                    st.success(f"合併完成，共 {len(sorted_names)} 個檔案")
                    st.download_button("⬇️ 下載合併後 PDF", result, "merged.pdf", "application/pdf")
                except Exception as e:
                    st.error(str(e))

# ── 拆分 ──────────────────────────────────────────────────────────────────────
elif tool == "✂️ 拆分 PDF":
    st.subheader("✂️ 拆分 PDF")

    uploaded = st.file_uploader("上傳 PDF", type="pdf")

    if uploaded:
        raw = uploaded.read()

        # 先讀頁數
        try:
            import pikepdf, io
            with pikepdf.open(io.BytesIO(raw)) as _pdf:
                total_pages = len(_pdf.pages)
            st.info(f"共 {total_pages} 頁")
        except Exception:
            total_pages = None

        mode = st.radio("拆分模式", ["每頁各一個檔", "每隔 N 頁", "自訂範圍"])

        if mode == "每頁各一個檔":
            if st.button("開始拆分", type="primary"):
                with st.spinner("拆分中..."):
                    try:
                        pages = split_pdf_every_page(raw)
                        st.success(f"共 {len(pages)} 頁")
                        st.download_button("⬇️ 下載 ZIP", pack_zip(pages), f"split_{uploaded.name}.zip", "application/zip")
                    except Exception as e:
                        st.error(str(e))

        elif mode == "每隔 N 頁":
            interval = st.number_input("每幾頁一個檔", min_value=1, max_value=total_pages or 9999, value=2, step=1)
            if st.button("開始拆分", type="primary"):
                with st.spinner("拆分中..."):
                    try:
                        pages = split_pdf_by_interval(raw, int(interval))
                        st.success(f"共拆出 {len(pages)} 個檔案")
                        st.download_button("⬇️ 下載 ZIP", pack_zip(pages), f"split_{uploaded.name}.zip", "application/zip")
                    except Exception as e:
                        st.error(str(e))

        elif mode == "自訂範圍":
            st.caption("每行輸入一個範圍，格式：起始頁-結束頁，例如：\n1-3\n5-8\n10-10")
            range_input = st.text_area("輸入範圍", placeholder="1-3\n5-8\n10-10")

            if st.button("開始拆分", type="primary"):
                try:
                    ranges = []
                    for line in range_input.strip().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("-")
                        if len(parts) != 2:
                            st.error(f"格式錯誤：{line}，請用「起始-結束」格式")
                            st.stop()
                        ranges.append((int(parts[0]), int(parts[1])))

                    with st.spinner("拆分中..."):
                        pages = split_pdf_by_ranges(raw, ranges)
                        st.success(f"共拆出 {len(pages)} 個檔案")
                        st.download_button("⬇️ 下載 ZIP", pack_zip(pages), f"split_{uploaded.name}.zip", "application/zip")
                except ValueError:
                    st.error("頁碼請輸入數字")
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
                st.success(f"轉換完成，共 {len(images)} 頁")
                st.download_button("⬇️ 下載 ZIP", pack_zip(images), f"{uploaded.name}_images.zip", "application/zip")
            except Exception as e:
                st.error(str(e))

# ── 圖片合成 PDF（拖拽排序）──────────────────────────────────────────────────
elif tool == "📑 圖片合成 PDF":
    st.subheader("📑 圖片合成 PDF")
    st.caption("上傳後可拖拽調整順序，再合成 PDF")

    uploaded = st.file_uploader(
        "上傳圖片（可多選）",
        type=["png", "jpg", "jpeg", "bmp", "tiff", "webp"],
        accept_multiple_files=True
    )

    if uploaded:
        file_map = {f.name: f for f in uploaded}
        sorted_names = sort_items(list(file_map.keys()), direction="vertical")
        st.caption("👆 拖拽上方列表調整順序")

        if st.button("開始合成", type="primary"):
            with st.spinner("合成中..."):
                try:
                    ordered_bytes = [file_map[n].read() for n in sorted_names]
                    result = images_to_pdf(ordered_bytes)
                    st.success("合成完成")
                    st.download_button("⬇️ 下載 PDF", result, "images_to_pdf.pdf", "application/pdf")
                except Exception as e:
                    st.error(str(e))
