import streamlit as st
from PIL import Image
import pandas as pd
import io
import os
import requests
from rembg import remove
import base64

st.set_page_config(page_title="Flaschenbild freistellen", layout="centered")

@st.cache_data
def load_sku_csv(path):
    df = pd.read_csv(
        path, sep=";", encoding="utf-8-sig", dtype={"sku": str}
    )
    df.columns = [c.strip() for c in df.columns]
    df["sku"] = df["sku"].astype(str).str.strip()
    return df

CSV_FILENAME = "banner_bilder_v1.csv"
if os.path.exists(CSV_FILENAME):
    df_skus = load_sku_csv(CSV_FILENAME)
else:
    df_skus = pd.DataFrame(columns=["sku", "bild", "hintergrundbild"])

st.title("📸 Remove Background from Bottle Images")

def limit_height(img, max_height=550):
    w, h = img.size
    if h > max_height:
        new_w = int(w * max_height / h)
        return img.resize((new_w, max_height))
    return img

def image_to_download_link(img, fname="original.png", mime="image/png"):
    buf = io.BytesIO()
    img.save(buf, format="PNG" if mime == "image/png" else "JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"<a href='data:{mime};base64,{b64}' download='{fname}'>Download original</a>"

col1, col2 = st.columns([1, 2])
with col1:
    uploaded_file = st.file_uploader(
        "Upload a bottle image (JPG, PNG, WEBP)",
        type=["png", "jpg", "jpeg", "webp"],
        key="uploader"
    )
    if uploaded_file:
        image_bytes = uploaded_file.read()
        image_input = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        st.session_state["freistell_image"] = image_input
        st.session_state["freistell_image_bytes"] = image_bytes
        st.session_state["freistell_sku"] = None

with col2:
    sku_input = st.text_input("Or enter product SKU (from CSV)", value="", key="sku_input")
    load_btn = st.button("🔎 Load image by SKU")
    if load_btn:
        sku_to_load = sku_input.strip()
        match = df_skus[df_skus["sku"] == sku_to_load]
        if match.empty:
            st.error("No image found for this SKU.")
        else:
            url_img = str(match["bild"].values[0]).strip()
            try:
                response = requests.get(url_img, timeout=10)
                image_bytes = response.content
                image_input = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
                st.session_state["freistell_image"] = image_input
                st.session_state["freistell_image_bytes"] = image_bytes
                st.session_state["freistell_sku"] = sku_to_load
            except Exception as e:
                st.error(f"Could not load image: {e}")

# ----- Immer Session-State verwenden -----
image_input = st.session_state.get("freistell_image", None)
image_bytes = st.session_state.get("freistell_image_bytes", None)
sku_for_save = st.session_state.get("freistell_sku", "")

if image_input is not None:
    st.markdown("---")
    img_caption = f"Original image" + (f" (SKU {sku_for_save})" if sku_for_save else "")
    st.image(limit_height(image_input), caption=img_caption, use_container_width=False)
    download_label = f"Download original" + (f" (SKU {sku_for_save})" if sku_for_save else "")
    st.markdown(
        image_to_download_link(
            image_input, 
            f"original_{sku_for_save or 'image'}.png"
        ), 
        unsafe_allow_html=True
    )

    st.markdown("---")
    export_fmt = st.radio(
        "Export format:",
        ["PNG (transparent background)", "JPEG (transparent background)"],
        horizontal=True
    )

    if st.button("🔍 Remove Background"):
        with st.spinner("Removing background..."):
            removed = remove(image_bytes)
            img_no_bg = Image.open(io.BytesIO(removed)).convert("RGBA")
            buf = io.BytesIO()
            file_ext = "png" if export_fmt.startswith("PNG") else "jpg"
            mime = "image/png" if export_fmt.startswith("PNG") else "image/jpeg"
            if export_fmt.startswith("PNG"):
                img_no_bg.save(buf, format="PNG")
            else:
                img_no_bg.save(buf, format="PNG")  # technically, JPEG does not support transparency; stay PNG!
            data = buf.getvalue()
            fname = f"freigestellt_{sku_for_save or 'image'}.{file_ext}"

            # Automatisch nur das gewünschte Format als Download
            b64 = base64.b64encode(data).decode()
            href = f"<a href='data:{mime};base64,{b64}' download='{fname}'>Download result</a>"
            st.success("Done! Click the link below to download your background-removed image.")
            st.markdown(href, unsafe_allow_html=True)
else:
    st.info("Please upload an image or select a SKU to start.")