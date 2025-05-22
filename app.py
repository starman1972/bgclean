"""
Streamlit application for removing backgrounds from bottle images.

This application allows users to upload an image or specify a product SKU
to load an image. It then provides functionality to remove the background
from the image and download the result in PNG or JPEG format.
"""
import streamlit as st
from PIL import Image
import pandas as pd
import io
import os
import requests
from rembg import remove
import base64
from typing import Tuple, Optional, List, Any 
from streamlit.runtime.uploaded_file_manager import UploadedFile

# --- Constants and Configuration ---
PAGE_TITLE: str = "Background Remover for Bottle Images"
SKU_CSV_FILENAME: str = "banner_bilder_v1.csv"
MAX_IMAGE_HEIGHT: int = 550
SUPPORTED_IMAGE_TYPES: List[str] = ["png", "jpg", "jpeg", "webp"]
DEFAULT_EXPECTED_COLUMNS: List[str] = ["sku", "image_url", "background_image_url"]
FALLBACK_IMAGE_URL_COLUMN: str = "bild"
FALLBACK_BACKGROUND_URL_COLUMN: str = "hintergrundbild"
REQUESTS_TIMEOUT: int = 10
EXPORT_FORMAT_PNG: str = "PNG (transparent background)"
EXPORT_FORMAT_JPEG: str = "JPEG (white background)"

# --- Initial Setup ---
st.set_page_config(page_title=PAGE_TITLE, layout="centered")

# --- Custom CSS ---
def apply_custom_css() -> None:
    """Applies custom CSS styles to the application."""
    st.markdown("""
    <style>
        /* General body style for slightly more modern font if available */
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
        }

        /* Style for primary action buttons - Streamlit's default is often good, 
           but this ensures they are prominent if specific styling was desired.
           The use_container_width=True on st.button is the primary driver of their visual weight.
        */
        div[data-testid="stButton"] > button {
            /* Example: font-weight: 600; */
        }

        /* Custom class for download links to look like subtle buttons */
        .download-link a {
            display: inline-block;
            padding: 0.4em 0.8em; /* Slightly larger padding */
            background-color: #f0f2f6; /* Light gray background - Streamlit's secondary_bg */
            color: #31333F; /* Streamlit's default text color */
            border: 1px solid #d4d4d8; /* Subtle border */
            border-radius: 0.3rem; /* Rounded corners */
            text-decoration: none; /* Remove underline */
            font-size: 0.95em; /* Slightly larger font */
            margin-top: 0.5em; /* Add some space above */
            transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out; /* Smooth transition */
        }
        .download-link a:hover {
            background-color: #e6e8eb; /* Slightly darker on hover */
            color: #090A0B; /* Darker text on hover */
            text-decoration: none;
        }
        .stAlert { /* Add some margin below alerts */
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---

@st.cache_data
def load_sku_data(path: str) -> pd.DataFrame:
    """
    Loads SKU data from a CSV file.
    Cleans column names, standardizes expected columns, and handles potential errors.
    """
    try:
        df: pd.DataFrame = pd.read_csv(
            path, sep=";", encoding="utf-8-sig", dtype={"sku": str}
        )
        df.columns = [str(col).strip().lower() for col in df.columns]
        if "sku" not in df.columns:
            st.error(f"Error: The CSV file at '{path}' must contain a 'sku' column for product identification.")
            return pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)
        df["sku"] = df["sku"].astype(str).str.strip()
        if "image_url" not in df.columns and FALLBACK_IMAGE_URL_COLUMN in df.columns:
            df.rename(columns={FALLBACK_IMAGE_URL_COLUMN: "image_url"}, inplace=True)
        if "background_image_url" not in df.columns and FALLBACK_BACKGROUND_URL_COLUMN in df.columns:
            df.rename(columns={FALLBACK_BACKGROUND_URL_COLUMN: "background_image_url"}, inplace=True)
        for col in DEFAULT_EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None # type: ignore 
        return df[DEFAULT_EXPECTED_COLUMNS]
    except FileNotFoundError:
        st.error(f"Error: The SKU data file '{path}' was not found. Please ensure the file exists in the correct location.")
        return pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)
    except Exception as e:
        st.error(f"An error occurred while loading the SKU data from '{path}': {e}. Please ensure the CSV file is correctly formatted and not corrupted.")
        return pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)

def resize_image(image: Image.Image, max_height: int = MAX_IMAGE_HEIGHT) -> Image.Image:
    width, height = image.size
    if height > max_height:
        new_width = int(width * max_height / height)
        return image.resize((new_width, max_height))
    return image

def generate_download_link(
    image: Image.Image, 
    filename: str, 
    link_text: str, 
    mime_type: str = "image/png"
) -> str:
    buffer = io.BytesIO()
    image_format = "PNG" if mime_type == "image/png" else "JPEG"
    image.save(buffer, format=image_format)
    b64_image = base64.b64encode(buffer.getvalue()).decode()
    # Apply the .download-link class to the div wrapping the anchor
    return f"<div class='download-link'><a href='data:{mime_type};base64,{b64_image}' download='{filename}'>{link_text}</a></div>"

def load_image_from_upload(uploaded_file: Optional[UploadedFile]) -> Tuple[Optional[Image.Image], Optional[bytes]]:
    if uploaded_file:
        image_bytes: bytes = uploaded_file.read()
        try:
            image: Image.Image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            return image, image_bytes
        except Exception as e:
            st.error(
                f"Error loading uploaded image ('{uploaded_file.name}'): {e}. "
                f"Please ensure it's a valid image file ({', '.join(SUPPORTED_IMAGE_TYPES)}) and not corrupted."
            )
            return None, None
    return None, None

def load_image_from_sku(sku: str, sku_df: pd.DataFrame) -> Tuple[Optional[Image.Image], Optional[bytes]]:
    if not sku:
        st.warning("Please enter a SKU to load an image.")
        return None, None
    if sku_df.empty or "sku" not in sku_df.columns or "image_url" not in sku_df.columns:
        st.error("SKU data is not available or missing required columns ('sku', 'image_url'). Please check the CSV file.")
        return None, None
    match: pd.DataFrame = sku_df[sku_df["sku"] == sku]
    if match.empty:
        st.error(f"No product image found for SKU: '{sku}'. Please check the SKU or the CSV file.")
        return None, None
    image_url_series = match["image_url"]
    image_url: Any = image_url_series.values[0] if not image_url_series.empty else None
    if pd.isna(image_url) or not str(image_url).strip():
        st.error(f"No image URL is available for SKU: '{sku}' in the CSV data (URL is empty or invalid).")
        return None, None
    image_url_str: str = str(image_url).strip()
    try:
        response: requests.Response = requests.get(image_url_str, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status() 
        image_bytes: bytes = response.content
        image: Image.Image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        return image, image_bytes
    except requests.exceptions.RequestException as e:
        st.error(
            f"Could not load image for SKU '{sku}' from URL '{image_url_str}'. "
            f"Please check if the URL is correct and accessible, or try again later. Network details: {e}"
        )
        return None, None
    except Exception as e:
        st.error(
            f"An unexpected error occurred while processing the image for SKU '{sku}' from '{image_url_str}': {e}. "
            "The image might be corrupted or in an unsupported format."
        )
        return None, None

def process_background_removal(image_bytes: bytes) -> Optional[Image.Image]:
    if not image_bytes: 
        st.error("No image data was provided to the background removal function.")
        return None
    try:
        with st.spinner("Removing background... This may take a moment."):
            removed_bg_bytes: bytes = remove(image_bytes)
            return Image.open(io.BytesIO(removed_bg_bytes)).convert("RGBA")
    except Exception as e:
        st.error(
            f"Background removal failed. This can occur with certain image types, "
            f"if the image is too complex, or due to server resource limits. "
            f"Please try a different image if the problem persists. Details: {e}"
        )
        return None

# --- Session State Management ---
def initialize_session_state() -> None:
    session_defaults: dict[str, Any] = {
        "current_image": None, "current_image_bytes": None, "current_sku": None,
        "sku_input_text": "", "last_uploaded_file_id": None,
    }
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def update_session_data(image: Optional[Image.Image], image_bytes: Optional[bytes], sku: Optional[str]) -> None:
    st.session_state["current_image"] = image
    st.session_state["current_image_bytes"] = image_bytes
    st.session_state["current_sku"] = sku
    st.session_state["sku_input_text"] = sku if sku else ""

def clear_session_image_data() -> None:
    st.session_state["current_image"] = None
    st.session_state["current_image_bytes"] = None
    st.session_state["current_sku"] = None

def get_session_image() -> Optional[Image.Image]:
    return st.session_state.get("current_image")

def get_session_image_bytes() -> Optional[bytes]:
    return st.session_state.get("current_image_bytes")

def get_session_sku() -> Optional[str]: 
    return st.session_state.get("current_sku")

# --- Main Application ---
def main() -> None:
    apply_custom_css() # Apply custom styles
    st.title(PAGE_TITLE)
    initialize_session_state()

    sku_df: pd.DataFrame = load_sku_data(SKU_CSV_FILENAME)
    if not os.path.exists(SKU_CSV_FILENAME):
        st.info(
            f"SKU data file ('{SKU_CSV_FILENAME}') not found. "
            "Image loading by SKU will be unavailable. Please ensure the CSV file is in the application's root directory."
        )
    elif sku_df.empty: 
        st.warning(
            f"SKU data from '{SKU_CSV_FILENAME}' could not be loaded or is empty. "
            "Please check the file format, content, and ensure it's not corrupted. "
            "Loading images by SKU may not work as expected."
        )
    
    with st.container(border=True): # Input section container
        st.subheader("Image Input Options")
        # st.markdown("---") # No longer needed due to container border

        input_col1, input_col2 = st.columns(2) 
        with input_col1:
            st.markdown("#### Upload Image File")
            uploaded_file: Optional[UploadedFile] = st.file_uploader(
                "Select a bottle image (JPG, PNG, WEBP)", 
                type=SUPPORTED_IMAGE_TYPES, key="uploader", label_visibility="collapsed" 
            )
            if uploaded_file:
                if uploaded_file.id != st.session_state.get("last_uploaded_file_id"):
                    st.session_state.last_uploaded_file_id = uploaded_file.id
                    img, img_bytes = load_image_from_upload(uploaded_file)
                    if img and img_bytes:
                        update_session_data(img, img_bytes, None) 

        with input_col2:
            st.markdown("#### Load Image by SKU")
            def sync_sku_input_text() -> None:
                st.session_state.sku_input_text = st.session_state.sku_input_widget_key
                if st.session_state.current_image is not None and st.session_state.current_sku is None:
                    clear_session_image_data()
            st.text_input(
                "Enter product SKU (from CSV):", key="sku_input_widget_key",
                value=st.session_state.sku_input_text, on_change=sync_sku_input_text,
                label_visibility="collapsed"
            )
            if st.button("🔎 Load image by SKU", key="load_sku_btn", use_container_width=True):
                sku_to_load: str = st.session_state.sku_input_text.strip()
                if sku_to_load:
                    clear_session_image_data() 
                    img, img_bytes = load_image_from_sku(sku_to_load, sku_df)
                    if img and img_bytes:
                        update_session_data(img, img_bytes, sku_to_load)
                else:
                    st.warning("Please enter a SKU to load an image.")
    
    # Removed st.markdown("---") here, container border serves as separator

    current_display_image: Optional[Image.Image] = get_session_image()
    current_display_image_bytes: Optional[bytes] = get_session_image_bytes()
    current_display_sku: Optional[str] = get_session_sku()

    if current_display_image:
        with st.container(border=True): # Image preview and processing container
            st.subheader("Image Preview & Processing")
            # st.markdown("---") # No longer needed

            display_caption: str = "Original Image"
            if current_display_sku: 
                display_caption += f" (SKU: {current_display_sku})"
            
            img_col, dl_col = st.columns([3,2]) 
            with img_col:
                st.image(resize_image(current_display_image), caption=display_caption, use_container_width=False)
            with dl_col:
                st.markdown("<br>", unsafe_allow_html=True) 
                download_filename_original: str = f"original_{current_display_sku or 'image'}.png"
                # generate_download_link now wraps its output in <div class='download-link'>...</div>
                st.markdown(
                    generate_download_link(
                        current_display_image, download_filename_original, 
                        f"Download Original ({current_display_sku or 'image'})"
                    ), unsafe_allow_html=True
                )

            st.markdown("---") # Separator within the processing container
            st.markdown("##### Background Removal Options")
            export_format_choice: str = st.radio( # type: ignore[assignment]
                "Export format:", [EXPORT_FORMAT_PNG, EXPORT_FORMAT_JPEG], 
                horizontal=True, key="export_format", label_visibility="collapsed"
            )

            if st.button("🎨 Remove Background", key="remove_bg_btn", use_container_width=True):
                if current_display_image_bytes:
                    processed_image: Optional[Image.Image] = process_background_removal(current_display_image_bytes)
                    if processed_image:
                        st.subheader("Processed Image") # This could be outside the button press if we want to keep it shown
                        proc_img_col, proc_dl_col = st.columns([3,2])
                        with proc_img_col:
                             st.image(resize_image(processed_image), caption="Background Removed", use_container_width=False)
                        
                        output_buffer = io.BytesIO()
                        file_extension: str = "png"
                        mime: str = "image/png"
                        if export_format_choice == EXPORT_FORMAT_JPEG:
                            file_extension = "jpg"; mime = "image/jpeg"
                            final_image_for_export: Image.Image = Image.new("RGB", processed_image.size, "WHITE")
                            final_image_for_export.paste(processed_image, (0,0), processed_image) 
                            final_image_for_export.save(output_buffer, format="JPEG")
                        else: # PNG
                            processed_image.save(output_buffer, format="PNG")
                        
                        image_data_for_download: bytes = output_buffer.getvalue()
                        download_filename_processed: str = f"removed_bg_{current_display_sku or 'image'}.{file_extension}"
                        
                        with proc_dl_col:
                            st.markdown("<br>", unsafe_allow_html=True) 
                            b64_processed: str = base64.b64encode(image_data_for_download).decode()
                            # generate_download_link now wraps its output in <div class='download-link'>...</div>
                            href_processed: str = (
                                f"<div class='download-link'><a href='data:{mime};base64,{b64_processed}' "
                                f"download='{download_filename_processed}'>"
                                f"Download Result ({current_display_sku or 'image'})</a></div>"
                            )
                            st.success("Background removal successful!")
                            st.markdown(href_processed, unsafe_allow_html=True)
                else: # current_display_image_bytes was None
                    st.error("No image data found to remove background from. Please upload or load an image first.")
    else: # No current_display_image
        st.markdown("<br>", unsafe_allow_html=True) # Add some space before the info message
        st.info("Welcome! Please upload an image or load one using a SKU to begin.")

if __name__ == "__main__":
    main()
