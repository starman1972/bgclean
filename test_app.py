import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from PIL import Image
from unittest.mock import patch, mock_open
import io

# Assuming app.py is in the same directory or accessible in PYTHONPATH
from app import load_sku_data, resize_image, DEFAULT_EXPECTED_COLUMNS, MAX_IMAGE_HEIGHT

# --- Tests for load_sku_data ---

def test_load_sku_data_success():
    """Test successful loading and processing of SKU data."""
    csv_data = (
        "sku;bild;hintergrundbild\n"
        " 123 ; http://example.com/img1.jpg ; http://example.com/bg1.jpg \n"
        "456;http://example.com/img2.jpg;http://example.com/bg2.jpg\n"
        "789 ; ; \n" # SKU with missing image URLs
    )
    
    expected_data = {
        "sku": ["123", "456", "789"],
        "image_url": ["http://example.com/img1.jpg", "http://example.com/img2.jpg", None],
        "background_image_url": ["http://example.com/bg1.jpg", "http://example.com/bg2.jpg", None],
    }
    expected_df = pd.DataFrame(expected_data)
    # Ensure correct dtypes for comparison, especially for None/NaN
    expected_df = expected_df.astype({
        "image_url": object, 
        "background_image_url": object
    })


    # Mock pd.read_csv to return our test CSV data
    with patch("pandas.read_csv", return_value=pd.read_csv(io.StringIO(csv_data), sep=";", dtype={"sku": str})) as mock_read_csv:
        df = load_sku_data("dummy_path.csv")
        mock_read_csv.assert_called_once_with(
            "dummy_path.csv", sep=";", encoding="utf-8-sig", dtype={"sku": str}
        )

    # Fill NaN with None for comparison, as read_csv might produce NaN for empty strings
    df_filled = df.fillna(value=pd.NA).replace({pd.NA: None})
    expected_df_filled = expected_df.fillna(value=pd.NA).replace({pd.NA: None})
    
    assert_frame_equal(df_filled, expected_df_filled, check_dtype=False)

def test_load_sku_data_missing_sku_column():
    """Test handling of CSV data missing the essential 'sku' column."""
    csv_data = "bild;hintergrundbild\nhttp://example.com/img1.jpg;http://example.com/bg1.jpg"
    
    # Expected empty DataFrame with default columns
    expected_df = pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)

    with patch("pandas.read_csv", return_value=pd.read_csv(io.StringIO(csv_data), sep=";")) as mock_read_csv:
        # Mock st.error as it's called when 'sku' column is missing
        with patch("app.st.error") as mock_st_error:
            df = load_sku_data("dummy_path.csv")
            mock_st_error.assert_called_once() 
    
    assert_frame_equal(df, expected_df, check_dtype=False)


def test_load_sku_data_file_not_found():
    """Test handling of FileNotFoundError when CSV file does not exist."""
    expected_df = pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)

    # Mock pd.read_csv to raise FileNotFoundError
    with patch("pandas.read_csv", side_effect=FileNotFoundError("File not found")) as mock_read_csv:
        # Mock st.error as it's called when file is not found
        with patch("app.st.error") as mock_st_error:
            df = load_sku_data("non_existent_path.csv")
            mock_st_error.assert_called_once()

    assert_frame_equal(df, expected_df, check_dtype=False)

def test_load_sku_data_other_exception():
    """Test handling of other exceptions during CSV parsing."""
    expected_df = pd.DataFrame(columns=DEFAULT_EXPECTED_COLUMNS)

    # Mock pd.read_csv to raise a generic Exception
    with patch("pandas.read_csv", side_effect=Exception("Some parsing error")) as mock_read_csv:
        with patch("app.st.error") as mock_st_error:
            df = load_sku_data("dummy_path.csv")
            mock_st_error.assert_called_once()
            
    assert_frame_equal(df, expected_df, check_dtype=False)

def test_load_sku_data_column_name_variations():
    """Test that column names are correctly standardized (lowercase, stripped)."""
    # Note: The function already standardizes 'bild' to 'image_url'.
    # This test focuses on general cleaning like spaces and case.
    csv_data = (
        " SKU ; Bild ; Hintergrundbild \n" # Note spaces and mixed case
        "abc;http://example.com/img.jpg;http://example.com/bg.jpg\n"
    )
    expected_data = {
        "sku": ["abc"],
        "image_url": ["http://example.com/img.jpg"],
        "background_image_url": ["http://example.com/bg.jpg"],
    }
    expected_df = pd.DataFrame(expected_data)
    expected_df = expected_df.astype({"image_url": object, "background_image_url": object})


    with patch("pandas.read_csv", return_value=pd.read_csv(io.StringIO(csv_data), sep=";", dtype={"sku": str})) as mock_read_csv:
        df = load_sku_data("dummy_path.csv")

    df_filled = df.fillna(value=pd.NA).replace({pd.NA: None})
    expected_df_filled = expected_df.fillna(value=pd.NA).replace({pd.NA: None})

    assert_frame_equal(df_filled, expected_df_filled, check_dtype=False)


# --- Tests for resize_image ---

def test_resize_image_larger_than_max():
    """Test resizing when image height is greater than max_height."""
    original_width = 800
    original_height = 600
    max_h = MAX_IMAGE_HEIGHT # Default max_height from app.py (550)
    
    # Ensure test max_height is less than original_height
    test_max_height = min(max_h, original_height - 50) 

    img = Image.new("RGB", (original_width, original_height))
    resized_img = resize_image(img, max_height=test_max_height)

    assert resized_img.height == test_max_height
    expected_width = int(original_width * test_max_height / original_height)
    assert resized_img.width == expected_width

def test_resize_image_smaller_than_max():
    """Test resizing when image height is less than or equal to max_height."""
    original_width = 400
    original_height = 300
    max_h = MAX_IMAGE_HEIGHT # 550

    img = Image.new("RGB", (original_width, original_height))
    
    # Case 1: max_height in function is the default MAX_IMAGE_HEIGHT from app
    resized_img_default = resize_image(img) # Uses default MAX_IMAGE_HEIGHT
    assert resized_img_default.height == original_height
    assert resized_img_default.width == original_width

    # Case 2: max_height passed is explicitly larger than image height
    test_max_height = original_height + 100
    resized_img_explicit = resize_image(img, max_height=test_max_height)
    assert resized_img_explicit.height == original_height
    assert resized_img_explicit.width == original_width

def test_resize_image_equal_to_max():
    """Test resizing when image height is equal to max_height."""
    original_width = 400
    original_height = MAX_IMAGE_HEIGHT # 550
    
    img = Image.new("RGB", (original_width, original_height))
    resized_img = resize_image(img) # Uses default MAX_IMAGE_HEIGHT

    assert resized_img.height == original_height
    assert resized_img.width == original_width

# To run these tests, navigate to the repository root in your terminal
# and execute: pytest
# Ensure app.py is in the same directory or accessible in PYTHONPATH.
# Also ensure necessary libraries (pandas, Pillow, pytest) are installed.
# Streamlit components (like st.error) are mocked where necessary.
# For a more isolated test of load_sku_data without mocking st.error,
# you might need to refactor st.error calls out or use a more complex mocking setup.
# However, for this basic unit test, mocking st.error is acceptable.
