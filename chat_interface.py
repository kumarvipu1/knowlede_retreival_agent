import streamlit as st
import json
from pathlib import Path
import base64
from PIL import Image
import os
from agent_module import run_agent
import asyncio
import nest_asyncio
import uuid
import re
from datetime import datetime
from typing import Annotated, List, Optional, Tuple
from markdown_pdf import MarkdownPdf, Section
from streamlit_elements import elements, mui, html, sync
import streamlit.components.v1 as components
from io import BytesIO

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Initialize session state
if "file_hashes" not in st.session_state:
    st.session_state.file_hashes = {}

@st.cache_data
def get_base64_image_src(img_path):
    """Caches and returns base64 encoded image source."""
    try:
        with open(img_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{img_data}" # Assuming png, adjust if needed
    except Exception as e:
        st.warning(f"Error loading document: {e}")
        return img_path
    

@st.cache_data
def get_resized_base64_image_src(img_path, max_width=1000, max_height=800):
    """Caches, resizes, and returns base64 encoded image source."""
    try:
        img = Image.open(img_path)
        img.thumbnail((max_width, max_height))  # Resize in place, aspect ratio preserved

        buffered = BytesIO()
        img.save(buffered, format="JPEG", optimize=True) # Use JPEG, optimize for size
        img_data = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_data}" # Changed to image/jpeg
    except Exception as e:
        st.warning(f"Error loading or resizing image: {e}")
        return get_base64_image_src(img_path)

@st.cache_data
def write_markdown_to_file(content: Annotated[str, "The markdown content to write"], 
                        filename: Annotated[str, "The name of the file (with or without .md extension)"] = "blog.md",
                        image_paths: Annotated[List[str], "The list of image paths to include in the markdown file"] = []) -> str:
    """
    Write markdown content to a file with .md extension and create PDF with appended images.
    Uses Streamlit caching to prevent redundant file operations.
    """
    try:
        # Ensure filename has .md extension
        md_filename = filename.replace('.pdf', '.md') if filename.endswith('.pdf') else filename
        pdf_filename = filename.replace('.md', '.pdf')
        
        # Create deterministic hash of content and image paths
        content_hash = hash(f"{content}_{tuple(image_paths)}")
        
        # Check if file exists and hash matches
        if md_filename in st.session_state.file_hashes:
            if st.session_state.file_hashes[md_filename] == content_hash:
                if os.path.exists(pdf_filename):
                    return f"File {filename} already exists with same content."

        # Update hash in session state
        st.session_state.file_hashes[md_filename] = content_hash

        # Append images to content as base64
        for img_path in image_paths:
            try:
                # Read and encode image
                image_data = get_resized_base64_image_src(img_path)
                # Get image extension
                ext = os.path.splitext(img_path)[1].lstrip('.')
                # Add image to markdown content
                content += f"\n\n<img src='{image_data}' style='width: 100%; page-break-before: always;'>\n"
            except Exception as e:
                st.warning(f"Failed to add image {img_path}: {str(e)}")
                continue
        
        # Write markdown content
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create PDF
        pdf = MarkdownPdf()
        pdf.add_section(Section(content, toc=False))
        pdf.save(pdf_filename)
        
        return f"File {filename} has been created successfully."
        
    except Exception as e:
        st.error(f"Error writing file: {str(e)}")
        return f"Error creating file {filename}: {str(e)}"



def create_slideshow(image_paths, height=800):
    # Ensure we have a list of image paths
    if not isinstance(image_paths, list):
        image_paths = [image_paths]
    
    # Take first 3 images from the list (or all if less than 3)
    images = image_paths
    
    # Generate the slides HTML dynamically
    slides_html = ""
    dots_html = ""
    
    for i, img_path in enumerate(images, 1):
        # Convert image to base64 for embedding directly in HTML
        try:
            with open(img_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                img_src = f"data:image/png;base64,{img_data}"
        except Exception as e:
            st.warning(f"Error loading image {img_path}: {e}")
            # Use the path directly as fallback
            img_src = img_path
            
        slides_html += f"""
        <div class="mySlides fade">
            <div class="numbertext">{i} / {len(images)}</div>
            <img src="{img_src}" class="slideshow-image" id="img-{i}" style="width:100%; height: auto; object-fit: contain;" onclick="openModal();currentModalSlide({i})">
            <div class="text">Image {i}</div>
        </div>
        """
        dots_html += f'<span class="dot" onclick="currentSlide({i})"></span> '

    # Modal content for popup images
    modal_content = ""
    for i, img_path in enumerate(images, 1):
        try:
            with open(img_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                img_src = f"data:image/png;base64,{img_data}"
        except Exception as e:
            img_src = img_path
            
        modal_content += f"""
        <div class="modal-slides">
            <img src="{img_src}" style="width:100%">
        </div>
        """

    # Create the complete HTML with the dynamic content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    * {{box-sizing: border-box;}}
    body {{font-family: Verdana, sans-serif; margin: 0;}}
    .mySlides {{display: none;}}
    img {{vertical-align: middle;}}

    .slideshow-container {{
        max-width: 1000px;
        position: relative;
        margin: 0 auto;
        height: auto;
    }}

    .text {{
        color: grey;
        font-size: 15px;
        padding: 8px 12px;
        position: absolute;
        bottom: 8px;
        width: 100%;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }}

    .numbertext {{
        color: grey;
        font-size: 12px;
        padding: 8px 12px;
        position: absolute;
        top: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }}

    .dot {{
        height: 15px;
        width: 15px;
        margin: 0 1px;
        background-color: #bbb;
        border-radius: 50%;
        display: inline-block;
        transition: background-color 0.6s ease;
        cursor: pointer;
        margin-bottom: 0;
        padding-bottom: 0;
        margin-top: -10px; /* Adjusted to bring slightly up in position */
    }}

    .active, .dot:hover {{
        background-color: #717171;
    }}

    .fade {{
        animation-name: fade;
        animation-duration: 0.5s;
    }}

    @keyframes fade {{
        from {{opacity: .4}} 
        to {{opacity: 1}}
    }}
    
    /* Zoom feature */
    .zoom-container {{
        position: relative;
        margin: auto;
    }}
    
    .zoom-lens {{
        position: absolute;
        border: 0px solid #d4d4d4;
        width: 60px;
        height: 60px;
        background-color: rgba(255, 255, 255, 0.4);
        display: none;
        pointer-events: none;
    }}
    
    .zoom-result {{
        position: absolute;
        border: 1px solid #d4d4d4;
        width: 200px;
        height: 200px;
        background-repeat: no-repeat;
        display: none;
        z-index: 999;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        background-color: white;
        overflow: visible;
    }}
    
    /* Modal (background) */
    .modal {{
        display: none;
        position: fixed;
        z-index: 1000;
        padding-top: 50px;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: auto;
        background-color: rgba(0,0,0,0.9);
    }}

    /* Modal Content */
    .modal-content {{
        position: relative;
        margin: auto;
        padding: 0;
        width: 90%;
        max-width: 1200px;
    }}

    /* The Close Button */
    .close {{
        color: white;
        position: absolute;
        top: 10px;
        right: 25px;
        font-size: 35px;
        font-weight: bold;
        transition: 0.3s;
        z-index: 1001;
    }}

    .close:hover,
    .close:focus {{
        color: #999;
        text-decoration: none;
        cursor: pointer;
    }}

    /* Hide the slides by default */
    .modal-slides {{
        display: none;
    }}

    /* Next & previous buttons */
    .prev,
    .next {{
        cursor: pointer;
        position: absolute;
        top: 50%;
        width: auto;
        padding: 16px;
        margin-top: -50px;
        color: white;
        font-weight: bold;
        font-size: 20px;
        transition: 0.6s ease;
        border-radius: 0 3px 3px 0;
        user-select: none;
        -webkit-user-select: none;
        background-color: rgba(0,0,0,0.3);
    }}

    /* Position the "next button" to the right */
    .next {{
        right: 0;
        border-radius: 3px 0 0 3px;
    }}

    /* On hover, add a black background color with a little bit see-through */
    .prev:hover,
    .next:hover {{
        background-color: rgba(0,0,0,0.8);
    }}
    
    /* Make images clickable */
    .slideshow-image {{
        cursor: pointer;
    }}

    /* Reduce dot container spacing */
    div[style*="text-align:center"] {{
        margin-top: 5px;
        margin-bottom: 0;
        padding-bottom: 0;
    }}

    /* Adjust dot spacing */
    .dot {{
        margin-bottom: 0;
        padding-bottom: 0;
        position: relative;
        top: -80px;
    }}
    </style>
    </head>
    <body>

    <div class="slideshow-container zoom-container">
        <div class="zoom-lens" id="lens"></div>
        <div class="zoom-result" id="result"></div>
        {slides_html}
    </div>
    <br>

    <div style="text-align:center">
        {dots_html}
    </div>
    
    <!-- The Modal/Lightbox -->
    <div id="imageModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <div class="modal-content">
            {modal_content}
            
            <a class="prev" onclick="plusModalSlides(-1)">&#10094;</a>
            <a class="next" onclick="plusModalSlides(1)">&#10095;</a>
        </div>
    </div>

    <script>
    let slideIndex = 1;
    let modalSlideIndex = 1;
    showSlides(slideIndex);
    
    // Next/previous controls
    function plusSlides(n) {{
        showSlides(slideIndex += n);
    }}
    
    // Thumbnail image controls
    function currentSlide(n) {{
        showSlides(slideIndex = n);
    }}
    
    function showSlides(n) {{
        let i;
        let slides = document.getElementsByClassName("mySlides");
        let dots = document.getElementsByClassName("dot");
        if (n > slides.length) {{slideIndex = 1}}
        if (n < 1) {{slideIndex = slides.length}}
        for (i = 0; i < slides.length; i++) {{
            slides[i].style.display = "none";
        }}
        for (i = 0; i < dots.length; i++) {{
            dots[i].className = dots[i].className.replace(" active", "");
        }}
        slides[slideIndex-1].style.display = "block";
        dots[slideIndex-1].className += " active";
        
        // Reset zoom for the new slide
        setupZoom();
    }}
    
    // Modal functions
    function openModal() {{
        document.getElementById("imageModal").style.display = "block";
    }}
    
    function closeModal() {{
        document.getElementById("imageModal").style.display = "none";
    }}
    
    function plusModalSlides(n) {{
        showModalSlides(modalSlideIndex += n);
    }}
    
    function currentModalSlide(n) {{
        showModalSlides(modalSlideIndex = n);
    }}
    
    function showModalSlides(n) {{
        let i;
        let slides = document.getElementsByClassName("modal-slides");
        if (n > slides.length) {{modalSlideIndex = 1}}
        if (n < 1) {{modalSlideIndex = slides.length}}
        for (i = 0; i < slides.length; i++) {{
            slides[i].style.display = "none";
        }}
        slides[modalSlideIndex-1].style.display = "block";
    }}
    
    // Close the modal when clicking outside of the image
    window.onclick = function(event) {{
        const modal = document.getElementById("imageModal");
        if (event.target == modal) {{
            closeModal();
        }}
    }}
    
    // Zoom functionality
    function setupZoom() {{
        const lens = document.getElementById("lens");
        const result = document.getElementById("result");
        const currentImage = document.querySelector(".mySlides:not([style*='display: none']) img");
        
        if (!currentImage) return;
        
        // Set up event listeners for the current image
        currentImage.addEventListener("mousemove", moveLens);
        currentImage.addEventListener("mouseenter", function() {{
            lens.style.display = "block";
            result.style.display = "block";
        }});
        currentImage.addEventListener("mouseleave", function() {{
            lens.style.display = "none";
            result.style.display = "none";
        }});
        
        function moveLens(e) {{
            let pos, x, y;
            // Prevent any other actions that may occur
            e.preventDefault();
            // Get the cursor's x and y positions:
            pos = getCursorPos(e);
            // Calculate the position of the lens:
            x = pos.x - (lens.offsetWidth / 4);
            y = pos.y - (lens.offsetHeight / 4);
            
            // Prevent the lens from being positioned outside the image:
            if (x > currentImage.width - lens.offsetWidth) {{x = currentImage.width - lens.offsetWidth;}}
            if (x < 0) {{x = 0;}}
            if (y > currentImage.height - lens.offsetHeight) {{y = currentImage.height - lens.offsetHeight;}}
            if (y < 0) {{y = 0;}}
            
            // Set the position of the lens:
            lens.style.left = x + "px";
            lens.style.top = y + "px";
            
            // Position the result div relative to the cursor
            result.style.left = (pos.x + 20) + "px";
            result.style.top = (pos.y - 20) + "px";
            
            // Display what the lens "sees" with 50% reduced magnification
            // Reduce the magnification by 50% by adjusting the cx and cy values
            const cx = (result.offsetWidth / lens.offsetWidth) * 0.5; // Reduced by 50%
            const cy = (result.offsetHeight / lens.offsetHeight) * 0.5; // Reduced by 50%
            
            result.style.backgroundImage = "url('" + currentImage.src + "')";
            result.style.backgroundSize = (currentImage.width * cx) + "px " + (currentImage.height * cy) + "px";
            result.style.backgroundPosition = "-" + (x * cx) + "px -" + (y * cy) + "px";
        }}
        
        function getCursorPos(e) {{
            let a, x = 0, y = 0;
            e = e || window.event;
            // Get the x and y positions of the image:
            a = currentImage.getBoundingClientRect();
            // Calculate the cursor's x and y coordinates, relative to the image:
            x = e.pageX - a.left;
            y = e.pageY - a.top;
            // Consider any page scrolling:
            x = x - window.pageXOffset;
            y = y - window.pageYOffset;
            return {{x : x, y : y}};
        }}
    }}
    
    // Initialize zoom for the first slide
    document.addEventListener("DOMContentLoaded", function() {{
        // Show first slide and set up zoom
        showSlides(1);
    }});
    </script>

    </body>
    </html> 
    """

    # Display using streamlit components
    components.html(html_content, height=height-50)




FIXED_CONTAINER_CSS = """
div[data-testid="stVerticalBlockBorderWrapper"]:has(div.fixed-container-{id}):not(:has(div.not-fixed-container)){{
    background-color: transparent;
    position: {mode};
    width: inherit;
    background-color: inherit;
    {position}: {margin};
    z-index: 999;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div.fixed-container-{id}):not(:has(div.not-fixed-container)) div[data-testid="stVerticalBlock"]:has(div.fixed-container-{id}):not(:has(div.not-fixed-container)) > div[data-testid="element-container"] {{
    display: none;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div.not-fixed-container):not(:has(div[class^='fixed-container-'])) {{
    display: none;
}}
""".strip()

MARGINS = {
    "top": "2.875rem",
    "bottom": "60px",
}

def st_fixed_container(
    *,
    height = None,
    border = None,
    mode = "fixed",
    position = "top",
    margin = None,
    key = None,
):
    if margin is None:
        margin = MARGINS[position]
    global fixed_counter
    fixed_container = st.container()
    non_fixed_container = st.container()
    css = FIXED_CONTAINER_CSS.format(
        mode=mode,
        position=position,
        margin=margin,
        id=key,
    )
    with fixed_container:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='fixed-container-{key}'></div>",
            unsafe_allow_html=True,
        )
    with non_fixed_container:
        st.markdown(
            f"<div class='not-fixed-container'></div>",
            unsafe_allow_html=True,
        )

    with fixed_container:
        # Only pass height if it's not None (Streamlit doesn't accept None for height)
        if height is not None:
            return st.container(height=height, border=border)
        else:
            return st.container(border=border)


def download_button(object_to_download, download_filename, button_text, document_path):

    with st.spinner("Generating PDF..."):
        write_markdown_to_file(object_to_download, download_filename, document_path)

    with open(download_filename.replace("assets", ""), "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    button_uuid = str(uuid.uuid4()).replace('-', '')
    button_id = re.sub('\d+', '', button_uuid)

    b64 = base64.b64encode(pdf_bytes).decode()

    custom_css = f""" 
        <style>
            #{button_id} {{
                background-color: rgb(255, 255, 255);
                color: rgb(38, 39, 48);
                padding: 0.25em 0.38em;
                position: relative;
                text-decoration: none;
                border-radius: 4px;
                border-width: 1px;
                border-style: solid;
                border-color: rgb(230, 234, 241);
                border-image: initial;
            }} 
            #{button_id}:hover {{
                border-color: rgb(246, 51, 102);
                color: rgb(246, 51, 102);
            }}
            #{button_id}:active {{
                box-shadow: none;
                background-color: rgb(246, 51, 102);
                color: white;
                }}
        </style> """

    dl_link = custom_css + f'<a download="{download_filename.replace("assets", "")}" id="{button_id}" href="data:file/txt;base64,{b64}">{button_text}</a><br></br>'

    return dl_link

# Cache the file loader
@st.cache_data
def load_image(image_path):
    try:
        return Image.open(image_path)
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

@st.cache_data
def load_pdf_as_base64(pdf_path):
    try:
        with open(pdf_path.replace("assets", ""), "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return None

def display_metrics(metrics_dict):
    """
    Display metrics in rows with expandable sections
    """
    # Add custom CSS for metric styling
    st.markdown("""
        <style>
        /* Make metric labels smaller and compact */
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        /* Make metric values smaller */
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
            font-weight: bold !important;
        }
        
        /* Style the metric containers */
        [data-testid="metric-container"] {
            padding: 0.5rem !important;
            margin-bottom: 0.5rem !important;
            background-color: #f0f2f6;
            border-radius: 5px;
        }
        
        /* Style expander headers */
        .streamlit-expanderHeader {
            font-size: 1rem !important;
            padding: 0.5rem !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        # Parse metrics if it's a string
        if isinstance(metrics_dict, str):
            try:
                metrics = json.loads(metrics_dict.replace("'", '"'))
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse metrics data: Invalid JSON format\nError: {str(e)}")
                return
        elif isinstance(metrics_dict, dict):
            metrics = metrics_dict
        else:
            st.error(f"Unexpected metrics data type: {type(metrics_dict)}. Expected string or dictionary.")
            return

        if not metrics:
            st.info("No metrics data available")
            return

        # Define metric categories and their display order
        metric_categories = {
            "🎯 Credit Rating": ["Rating", "Outlook"],
            "📈 GDP Performance": ["GDP Growth", "GDP Projection", "Past Five Years Average"],
            "💰 Financial Indicators": ["Inflation", "Foreign Reserves", "Import Cover"],
            "🚢 Export Performance": ["Export Earnings", "Export Growth"],
            "📦 Key Exports": ["Key Commodity Exports"],
            "👥 Government Statistics": ["Government Capital Spending"],
            "⚠️ Risk Factors": ["Economic Constraints"],
            "🏭 Major Industries": ["Major Industries"]
        }

        # Display metrics by category in rows
        for category, metric_keys in metric_categories.items():
            with st.expander(category, expanded=True):
                # For metrics that match this category
                matching_metrics = []
                for key in metrics.keys():
                    if any(metric_key.lower() in key.lower() for metric_key in metric_keys):
                        matching_metrics.append((key, metrics[key]))
                
                if matching_metrics:
                    # Create appropriate number of columns based on metrics count
                    num_metrics = len(matching_metrics)
                    cols = st.columns(min(4, num_metrics))  # Max 4 metrics per row
                    
                    for idx, (key, value) in enumerate(matching_metrics):
                        try:
                            # Calculate which column to use
                            col_idx = idx % len(cols)
                            
                            with cols[col_idx]:
                                if isinstance(value, dict):
                                    # Handle nested dictionaries
                                    for sub_key, sub_value in value.items():
                                        st.metric(
                                            label=f"{key} - {sub_key}",
                                            value=("• " + "\n• ".join(str(x) for x in sub_value)) if isinstance(sub_value, list) else (str(sub_value) + "\n" if sub_value is not None else "N/A")
                                        )
                                elif isinstance(value, list):
                                    # Handle lists
                                    if not value:
                                        st.metric(label=key, value="No data")
                                    else:
                                        # Show first item as main metric
                                        st.metric(label=key, value=str(value[0]))
                                        # Show remaining items as bullet points
                                        if len(value) > 1:
                                            st.markdown(f"**Additional {key}:**")
                                            for item in value[1:]:
                                                st.markdown(f"• {item}")
                                else:
                                    # Handle single values
                                    display_value = (
                                        str(value) if value is not None and value != "" 
                                        else "N/A"
                                    )
                                    st.metric(label=key, value=display_value)
                            
                            # Add a new row after every 4 metrics
                            if (idx + 1) % 4 == 0 and idx < len(matching_metrics) - 1:
                                st.write("")  # Add space between rows
                                cols = st.columns(min(4, len(matching_metrics) - idx - 1))
                                
                        except Exception as e:
                            st.warning(f"Error displaying metric '{key}': {str(e)}")
                            continue

    except Exception as e:
        st.error(f"""
        Error processing metrics visualization
        Error type: {type(e).__name__}
        Error details: {str(e)}
        """)
        st.error("Problematic metrics data:")
        st.code(str(metrics_dict))

# Create a new event loop for async operations
def get_agent_response(user_query):
    try:
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the agent in the new event loop
        response = run_agent(user_query)
        
        # Close the loop
        loop.close()
        
        return response
    except Exception as e:
        st.error(f"Error in agent response: {str(e)}")
        return None

def set_page_config():
    """Configure the page with logo and custom styling"""
    st.set_page_config(
        page_title="Research Agent",
        page_icon="📊",
        layout="wide"
    )
    
    # Add custom CSS for the logo and header
    st.markdown("""
        <style>
        /* Hide default Streamlit header */
        header[data-testid="stHeader"] {
            display: none;
        }
        
        /* Remove default margins and padding */
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            margin-top: 0 !important;
        }
        
        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
            overflow: hidden !important;
        }

        section[data-testid="stSidebar"] {
            margin-top: 90px !important;
        }
        
        /* Frosted glass header */
        .logo-container {
            position: fixed;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 3rem;
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            margin: 0;
            width: 100vw;
            height: 90px;
            left: 50%;
            right: 50%;
            margin-left: -50vw;
            margin-right: -50vw;
            border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            top: 0;
            z-index: 1000;
        }
        
        /* Left section with Agusto logo and title */
        .left-section {
            display: flex;
            align-items: center;
        }
        
        .agusto-logo {
            height: 60px;
            margin-right: 20px;
            object-fit: contain;
        }
        
        /* Right section with Vizyx logo and powered by text */
        .right-section {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: center;
        }
        
        .vizyx-logo {
            height: 40px;
            object-fit: contain;
            margin-bottom: 4px;
        }
        
        .powered-by {
            color: #666;
            font-size: 12px;
            margin: 0;
            padding: 0;
        }

        /* Frosted glass footer */
        .footer-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            padding: 1rem 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .footer-text {
            color: rgba(0, 0, 0, 0.7);
            font-size: 0.8rem;
        }

        /* Adjust main content to account for footer */
        .main-content {
            padding-top: 90px !important;
            padding-bottom: 60px !important;
            margin-top: 0 !important;
        }

        /* Prevent horizontal scroll */
        body {
            overflow-x: hidden !important;
        }

        .title-container {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 2px;  /* Reduced spacing between title and subtitle */
        }
        
        .main-title {
            color: #2a1f5f;
            font-size: 24px;
            margin: 0;
            padding: 0;
            font-weight: bold;
            line-height: 1;  /* Reduced line height */
        }
        
        .sub-title {
            color: #4f4f4f;
            font-size: 16px;
            margin: 2px 0 0 0;  /* Reduced top margin */
            padding: 0;
            line-height: 1;  /* Reduced line height */
        }

        /* Gradient background for the entire app */
        .stApp {
            background: linear-gradient(135deg, 
                #f5f7fa 10%, 
                #e8edf5 35%, 
                #e0e9f0 60%, 
                #d8e5eb 85%, 
                #d0e1e6 100%) !important;
            background-attachment: fixed !important;
        }

        /* Make main content area transparent to show gradient */
        [data-testid="stAppViewContainer"] {
            background: transparent !important;
        }

        /* Chat message styling with semi-transparent background */
        [data-testid="stChatMessage"] {
            border: 1px solid rgba(220, 220, 220, 0.8);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            background-color: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* Style user messages */
        [data-testid="stChatMessage"][data-testid="user"] {
            border-left: 4px solid #0066cc;
            background-color: rgba(255, 255, 255, 0.7) !important;
        }

        /* Style assistant messages */
        [data-testid="stChatMessage"][data-testid="assistant"] {
            border-left: 4px solid #00cc88;
            background-color: rgba(255, 255, 255, 0.7) !important;
            margin-top: 0.5rem; /* Reduced top margin by 50% */
        }

        /* Style columns inside chat messages */
        [data-testid="stChatMessage"] > div > div > div > div[data-testid="column"] {
            background-color: rgba(250, 250, 250, 0.3) !important;
            padding: 1rem;
            border-radius: 8px;
        }

        /* Style metrics section */
        [data-testid="stChatMessage"] .stMetric {
            background-color: rgba(255, 255, 255, 0.7) !important;
            padding: 0.5rem;
            border-radius: 5px;
            border: 1px solid rgba(240, 240, 240, 0.5);
        }

        /* Style document preview section */
        [data-testid="stChatMessage"] img {
            border: 1px solid rgba(0, 0, 0, 0.5);
            border-radius: 10px;
        }

        /* Style sidebar with gradient */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, 
                rgba(255, 255, 255, 0.9) 0%, 
                rgba(255, 255, 255, 0.8) 100%) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        /* Keep header solid */
        .logo-container {
            background-color: white !important;
            border-bottom: 1px solid rgba(229, 229, 229, 0.5);
        }

        /* Style chat input container */
        .stChatInputContainer {
            background-color: rgba(255, 0, 0, 1) !important;
            border-radius: 10px;
            padding: 1rem;
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
        }

        /* Add spacing between sections */
        [data-testid="stChatMessage"] .stMarkdown {
            margin-bottom: 1rem;
        }

        /* Ensure text remains readable */
        .stMarkdown {
            color: #1f1f1f !important;
        }

        /* Enhanced frosted glass effect for both header and footer */
        .glass-effect {
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px) saturate(100%) !important;
            -webkit-backdrop-filter: blur(10px) saturate(100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1) !important;
        }

        /* Footer styling */
        .footer-content {
            position: fixed !important;
            bottom: 15px !important;
            left: 0 !important;
            right: 0 !important;
            height: 30px !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 0.3rem 3rem !important;
            font-size: 0.75rem !important;
            color: rgba(0, 0, 0, 0.6) !important;
            z-index: 998 !important;
            background: none !important;
        }

        /* Style the chat input container */
        .stChatInputContainer {
            padding: 10px;
        }
        
        /* Style the chat input box */
        .stChatInput {
            border: 1px solid grey !important;
            border-radius: 8px !important;
        }
        
        /* Style the chat input when focused */
        .stChatInput:focus {
            border: 1px solid grey !important;
            box-shadow: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

def get_base64_encoded_image(image_path):
    """Get base64 encoded image"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def main():
    # Set page configuration and styling
    set_page_config()
    
    # Display header with both logos
    agusto_logo_path = "assets/vizyx_logo.png"
    vizyx_logo_path = "assets/vizyx_logo.png"
    
    # Header HTML
    header_html = f"""
        <div class="logo-container glass-effect">
            <div class="left-section">
                <img src="data:image/jpg;base64,{get_base64_encoded_image(agusto_logo_path)}" alt="Agusto Logo" class="agusto-logo"/>
                <div class="title-container">
                    <h2 class="main-title">Research Agent</h2>
                    <p class="sub-title">AI-Powered Research</p>
                </div>
            </div>
            <div class="right-section">
                <img src="data:image/png;base64,{get_base64_encoded_image(vizyx_logo_path)}" alt="Vizyx Logo" class="vizyx-logo"/>
                <p class="powered-by">Powered by Vizyx</p>
            </div>
        </div>
        <div class="main-content">
    """

    # Footer HTML
    footer_html = f"""
        <div class="footer-content">
            <span>© {datetime.now().year} Vizyx Ltd. All rights reserved. For demonstration purposes only.</span>
        </div>
    """

    # Display header and footer
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.title("Knowledge Base Agent")
    st.write("Welcome to the Knowledge Base Agent - Agent for Knowledge Base Analysis")

    # Fixed chat input at bottom - responsive design
    st.markdown("""
        <style>
        /* Fixed chat input container at bottom */
        .stChatInput {
            position: fixed !important;
            bottom: 70px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 90% !important;
            max-width: 800px !important;
            z-index: 1000 !important;
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
            padding: 8px 16px !important;
            box-sizing: border-box !important;
        }
        
        /* Responsive adjustments for different screen sizes */
        @media (min-width: 768px) {
            .stChatInput {
                width: 80% !important;
                max-width: 900px !important;
            }
        }
        
        @media (min-width: 1200px) {
            .stChatInput {
                width: 60% !important;
                max-width: 1000px !important;
            }
        }
        
        @media (min-width: 1600px) {
            .stChatInput {
                width: 50% !important;
                max-width: 1000px !important;
            }
        }
        
        /* Add padding to bottom of main content to prevent overlap */
        .main .block-container {
            padding-bottom: 140px !important;
        }
        
        /* Style the chat input textarea */
        .stChatInput textarea {
            border: none !important;
            background: transparent !important;
            width: 100% !important;
        }
        
        .stChatInput textarea:focus {
            box-shadow: none !important;
            outline: none !important;
        }
        
        /* Ensure the input container doesn't overflow */
        .stChatInput > div {
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    user_query = st.chat_input("Enter your query")



    if user_query:
        # Show spinner while processing
        with st.spinner(f"Processing response for: {user_query}..."):
            try:
                # Get response from agent
                response = get_agent_response(user_query)
                
                if response:
                    # Validate metrics_dict before adding to history
                    if hasattr(response, 'metrics_dict'):
                        try:
                            # Test parsing of metrics_dict
                            if isinstance(response.metrics_dict, str):
                                json.loads(response.metrics_dict.replace("'", '"'))
                        except json.JSONDecodeError as e:
                            st.warning(f"Invalid metrics format in response: {str(e)}")
                            response.metrics_dict = "{}"  # Set empty metrics if invalid
                    else:
                        st.warning("Response missing metrics_dict attribute")
                        response.metrics_dict = "{}"

                    # Add to chat history (new messages at the beginning)
                    st.session_state.chat_history.insert(0, {
                        "query": user_query,
                        "response": response,
                        "timestamp": datetime.now().isoformat()  # Add timestamp for unique keys
                    })
                    # Trigger rerun to update the UI
                    st.rerun()
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")

    # Display chat history
    for idx, chat in enumerate(st.session_state.chat_history):
        # User message
        with st.chat_message("user"):
            st.write(chat["query"])
        
        # Assistant response
        with st.chat_message("assistant"):
            try:
                # Create two columns: one for content, one for document preview
                col1, col2 = st.columns([5, 3])
                
                with col1:
                    # Display markdown report with unique key
                    st.markdown(
                        chat["response"].markdown_report.replace("![](assets/vizyx_logo.png)", "")
                    )
                    
                    # Add download button for PDF with error handling and unique key
                    if chat["response"].pdf_path:
                        st.markdown(
                                    download_button(
                                        chat["response"].markdown_report.replace("output/", ""),
                                        chat["response"].pdf_path.replace("output/", ""),
                                        "Download Report PDF",
                                        chat["response"].document_path
                                    ),
                            unsafe_allow_html=True
                        )

                    st.markdown("--------------------------------")
                    
                    st.markdown("\n\n\n\n\n")
                
                with col2:
                    # Display document preview with error handling
                    st.subheader("Document Preview")
                    if chat["response"].document_path:
                        try:
                            with st.container():
                                st.markdown("""
                                    <style>
                                        .document-preview {
                                            max-height: 1000px;
                                            overflow-y: auto;
                                            padding: 2px;
                                            margin-bottom: 0;
                                        }
                                        .stSubheader {
                                            margin-bottom: 0 !important;
                                            padding-bottom: 0 !important;
                                        }
                                        /* Adjust slideshow container height and spacing */
                                        .slideshow-container {
                                            height: auto !important;
                                            min-height: 800px !important;
                                            margin-bottom: 40px !important; /* Add space for dots */
                                            position: relative;
                                        }
                                        /* Ensure images fill the container */
                                        .slideshow-image {
                                            height: 800px !important;
                                            width: 100% !important;
                                            object-fit: contain !important;
                                        }
                                        /* Fix dots container position */
                                        .dots-container {
                                            position: absolute;
                                            bottom: -30px;
                                            left: 0;
                                            right: 0;
                                            text-align: center;
                                            background: rgba(255, 255, 255, 0.8);
                                            padding: 5px 0;
                                            z-index: 100;
                                        }
                                        /* Style the dots */
                                        .dot {
                                            position: static !important;
                                            top: auto !important;
                                            margin: 0 4px !important;
                                        }
                                    </style>
                                """, unsafe_allow_html=True)

                                image_paths = chat["response"].document_path
                                create_slideshow(image_paths, height=1000)  # Increased height to accommodate dots
                        except Exception as e:
                            st.info(f"No document preview available")

            
            except Exception as e:
                st.warning(f"""
                Error displaying chat response
                Error type: {type(e).__name__}
                Error details: {str(e)}
                """
                )
        st.markdown("--------------------------------")

    # Display footer at the end
    st.markdown(footer_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
