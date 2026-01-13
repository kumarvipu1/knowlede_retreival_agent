import os
import re
import sys
from pathlib import Path
from pdf2image import convert_from_path
import PyPDF2

# Define the documents directory path
DOCUMENTS_DIR = Path("documents")

def check_poppler():
    """
    Check if Poppler is installed and return the path or None.
    On Windows, pdf2image requires Poppler to be installed separately.
    """
    try:
        # Try importing convert_from_path which requires poppler
        from pdf2image import convert_from_path
        
        # Try a simple conversion to check if poppler works
        test_pdf = next(DOCUMENTS_DIR.glob("*.pdf"), None)
        if test_pdf:
            # Just try to get the first page to test
            convert_from_path(test_pdf, first_page=1, last_page=1)
            return True
        return True  # No PDFs found, but we'll assume Poppler is working
    except Exception as e:
        if "poppler" in str(e).lower():
            return False
        # If error is not related to poppler, assume it's available
        return True

def sanitize_filename(filename):
    """Remove characters that are invalid in file names."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def convert_pdf_to_images():
    """
    Convert each page of all PDF files in the documents directory to PNG images.
    Creates a subfolder for each PDF and saves each page as PNG inside it.
    """
    # Check for Poppler dependency on Windows
    if sys.platform.startswith("win") and not check_poppler():
        print("\nERROR: Poppler is not installed or not found in your system path.")
        print("For Windows, you need to install Poppler for pdf2image to work:")
        print("1. Download Poppler for Windows from: https://github.com/oschwartz10612/poppler-windows/releases/")
        print("2. Extract the downloaded file to a location on your computer")
        print("3. Add the 'bin' directory to your system PATH, or provide the path to poppler in the script")
        print("\nAlternatively, you can specify the poppler_path in the convert_from_path function:")
        print("images = convert_from_path(pdf_path, poppler_path='C:\\path\\to\\poppler-xx\\bin')")
        return

    # Make sure the documents directory exists
    if not DOCUMENTS_DIR.exists():
        print(f"Error: The directory '{DOCUMENTS_DIR}' does not exist.")
        return

    # List all PDF files in the documents directory
    pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{DOCUMENTS_DIR}'.")
        return
    
    print(f"Found {len(pdf_files)} PDF files.")
    
    # Process each PDF file
    for pdf_path in pdf_files:
        pdf_name = pdf_path.stem  # Get the file name without extension
        sanitized_pdf_name = sanitize_filename(pdf_name)
        
        # Create a subfolder for this PDF
        output_dir = DOCUMENTS_DIR / sanitized_pdf_name
        output_dir.mkdir(exist_ok=True)
        
        print(f"Processing: {pdf_name}")
        
        try:
            # Get the number of pages in the PDF
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
            
            print(f"Converting {num_pages} pages to PNG images...")
            
            # Convert each page to an image
            # If you have Poppler installed but it's not in PATH, uncomment and modify the line below:
            # images = convert_from_path(pdf_path, dpi=300, fmt='png', poppler_path='C:\\path\\to\\poppler-xx\\bin')
            images = convert_from_path(
                pdf_path,
                dpi=300,  # You can adjust DPI for quality
                fmt='png',
                thread_count=os.cpu_count()
            )
            
            # Save each image
            for i, image in enumerate(images):
                page_num = i + 1  # Pages are 1-indexed for naming
                image_path = output_dir / f"{sanitized_pdf_name}_page_{page_num}.png"
                image.save(image_path, "PNG")
                print(f"  Saved: {image_path.name}")
            
            print(f"Successfully processed: {pdf_name}")
        
        except Exception as e:
            print(f"Error processing {pdf_name}: {e}")

if __name__ == "__main__":
    print("Starting PDF to PNG conversion...")
    convert_pdf_to_images()
    print("Conversion complete!") 