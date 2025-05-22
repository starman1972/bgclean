# bgclean - Background Remover

## 📸 Project Description

`bgclean` is a Streamlit web application designed to easily remove backgrounds from images. While it can be used for various types of images, it's particularly handy for product images, such as bottles, to create clean cutouts for e-commerce or marketing materials. The application leverages the `rembg` library for efficient background removal.

## ✨ Features

*   **AI-Powered Background Removal**: Utilizes the `rembg` library to automatically identify and remove image backgrounds.
*   **Multiple Input Methods**:
    *   **Direct Upload**: Upload your images directly in PNG, JPG, JPEG, or WEBP formats.
    *   **SKU-based Loading**: Load images by providing a product SKU. This feature requires a local CSV file (`banner_bilder_v1.csv`) mapping SKUs to image URLs.
*   **Image Previews**: Displays both the original and the processed (background-removed) images for easy comparison.
*   **Flexible Download Options**: Download the processed image in:
    *   PNG format (with a transparent background).
    *   JPEG format (with a white background).
*   **User-Friendly Interface**: Simple and intuitive web interface built with Streamlit.
*   **Customizable Display**: Images are resized for consistent display while maintaining aspect ratio.

## 🛠️ Tech Stack

*   **Python**: Core programming language.
*   **Streamlit**: For building the interactive web application interface.
*   **rembg**: The core library used for background removal.
*   **Pillow (PIL)**: For image manipulation tasks.
*   **Pandas**: For handling the SKU data from the CSV file.
*   **Requests**: For fetching images from URLs (used with the SKU feature).

## 🚀 Setup and Local Execution

Follow these steps to set up and run `bgclean` on your local machine.

### 1. Prerequisites

*   Python 3.7 or newer.

### 2. Clone Repository

```bash
git clone <your_repository_url> # Replace <your_repository_url> with the actual URL
cd bgclean # Or your repository's directory name
```

### 3. Create and Activate Virtual Environment (Recommended)

```bash
python -m venv venv
```

*   On macOS and Linux:
    ```bash
    source venv/bin/activate
    ```
*   On Windows:
    ```bash
    venv\Scripts\activate
    ```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Prepare SKU Data File (Optional, for "Load by SKU" feature)

If you plan to use the "Load image by SKU" feature, you need to create a CSV file named `banner_bilder_v1.csv` in the root directory of the project.

*   **Filename**: `banner_bilder_v1.csv`
*   **Separator**: Semicolon (`;`)
*   **Encoding**: UTF-8 (preferably `utf-8-sig` to handle potential BOM characters)
*   **Required Columns**:
    *   `sku`: The product Stock Keeping Unit (unique identifier).
    *   `image_url` (or `bild`): The direct URL to the product image.
*   **Optional Column**:
    *   `background_image_url` (or `hintergrundbild`): URL for a background image (currently not used by this specific version of the app for background removal but good to know if the CSV has it).

    The application will attempt to map `bild` to `image_url` and `hintergrundbild` to `background_image_url` if the primary English names are not found. Column names are case-insensitive and will be stripped of leading/trailing spaces.

*   **Example `banner_bilder_v1.csv` content**:

    ```csv
    sku;bild;hintergrundbild
    SKU001;https://example.com/images/bottle1.jpg;
    SKU002;http://my-cdn.com/path/to/image2.png;https://example.com/bg/bg2.jpg
    SKU003;https://another-site.net/product-images/item3.webp;
    ```

### 6. Run the Application

Once the setup is complete, run the Streamlit application:

```bash
streamlit run app.py
```

The application should open in your default web browser.

## 📖 Usage

1.  **Provide an Image**:
    *   **Option 1 (Upload)**: Click "Select a bottle image (JPG, PNG, WEBP)" under the "Upload Image File" section to choose an image from your computer.
    *   **Option 2 (SKU)**: If you have configured `banner_bilder_v1.csv`, enter a valid product SKU in the text field under "Load Image by SKU" and click "Load image by SKU".
2.  **Preview Original**: The uploaded/loaded image will be displayed under "Image Preview & Processing". You can download this original image using the link provided.
3.  **Remove Background**:
    *   Choose your desired "Export format" (PNG for transparency, JPEG for white background).
    *   Click the "Remove Background" button.
4.  **Preview and Download Result**:
    *   The background-removed image will appear under "Processed Image".
    *   Click the "Download Result" link to save the processed image.

## 🙌 Contributing

Contributions are welcome! If you have suggestions for improvements, new features, or find any bugs, please feel free to:

*   Open an issue in the repository.
*   Submit a pull request with your changes.

---

Enjoy using `bgclean`!
