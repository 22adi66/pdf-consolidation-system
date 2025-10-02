"""
Streamlit Frontend for PDF Consolidation System
Allows users to upload a ZIP file containing eCRF PDFs and download the consolidated output
"""

import streamlit as st
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from pdf_consolidation_backend import PDFConsolidationPipeline

# Page configuration
st.set_page_config(
    page_title="eCRF PDF Consolidation Tool",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">📄 eCRF PDF Consolidation Tool</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload a ZIP file containing multiple versions of eCRF PDFs to generate a consolidated output</p>', unsafe_allow_html=True)

# Sidebar with instructions
with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    ### How to use:
    
    1. **Prepare your files:**
       - Collect all eCRF PDF versions
       - Ensure filenames contain version numbers (e.g., `study-design-1-0-16.pdf`)
    
    2. **Create a ZIP file:**
       - Put all PDF files in a folder
       - Compress the folder into a ZIP file
    
    3. **Upload:**
       - Click the upload button
       - Select your ZIP file
    
    4. **Process:**
       - Click "Process PDFs"
       - Wait for consolidation to complete
    
    5. **Download:**
       - Download the consolidated PDF
    
    ---
    
    ### Features:
    - ✅ Automatic version detection
    - ✅ Bookmark preservation
    - ✅ Duplicate bookmark handling
    - ✅ Version tracking for changes
    - ✅ New bookmark insertion
    """)
    
    st.header("ℹ️ About")
    st.markdown("""
    This tool consolidates multiple versions of eCRF PDFs into a single document with:
    - **Version tracking** for modified sections
    - **Preserved bookmarks** including duplicates
    - **Smart comparison** algorithm
    - **Clean output** with hierarchical bookmarks
    """)

# Main content area
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    # File uploader
    st.subheader("📤 Upload ZIP File")
    uploaded_file = st.file_uploader(
        "Choose a ZIP file containing eCRF PDFs",
        type=['zip'],
        help="Upload a ZIP file containing multiple versions of eCRF PDFs"
    )
    
    if uploaded_file is not None:
        # Display file info
        st.markdown(f"""
        <div class="info-box">
            <strong>📦 Uploaded File:</strong> {uploaded_file.name}<br>
            <strong>📊 File Size:</strong> {uploaded_file.size / 1024:.2f} KB
        </div>
        """, unsafe_allow_html=True)
        
        # Process button
        if st.button("🚀 Process PDFs", type="primary", use_container_width=True):
            # Create temporary directories
            temp_dir = tempfile.mkdtemp()
            extract_dir = os.path.join(temp_dir, "extracted")
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(extract_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                # Extract ZIP file
                with st.spinner("📂 Extracting ZIP file..."):
                    zip_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(zip_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    # Find all PDF files
                    pdf_files = []
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if file.lower().endswith('.pdf'):
                                pdf_files.append(os.path.join(root, file))
                    
                    st.success(f"✅ Extracted {len(pdf_files)} PDF files")
                
                if len(pdf_files) == 0:
                    st.error("❌ No PDF files found in the ZIP archive!")
                elif len(pdf_files) == 1:
                    st.warning("⚠️ Only one PDF file found. Need at least 2 versions to consolidate.")
                else:
                    # Display found PDFs
                    with st.expander(f"📄 Found {len(pdf_files)} PDF files", expanded=False):
                        for pdf_file in pdf_files:
                            st.text(f"• {os.path.basename(pdf_file)}")
                    
                    # Run consolidation pipeline
                    with st.spinner("🔄 Processing PDFs... This may take a few moments..."):
                        # Create progress container
                        progress_container = st.container()
                        
                        with progress_container:
                            st.info("⏳ Analyzing PDF versions...")
                            
                            # Determine input directory (find the directory containing PDFs)
                            input_dir = os.path.dirname(pdf_files[0]) if len(pdf_files) > 0 else extract_dir
                            
                            # Run pipeline
                            pipeline = PDFConsolidationPipeline(
                                input_dir=input_dir,
                                output_dir=output_dir
                            )
                            
                            st.info("🔍 Comparing PDF versions...")
                            result = pipeline.run()
                            
                            if result['success']:
                                st.success("✅ PDF consolidation completed successfully!")
                                
                                # Display statistics
                                st.markdown(f"""
                                <div class="success-box">
                                    <h4>📊 Processing Summary</h4>
                                    <ul>
                                        <li><strong>Total PDFs Processed:</strong> {result['stats']['total_pdfs']}</li>
                                        <li><strong>Total Pages:</strong> {result['stats']['total_pages']}</li>
                                        <li><strong>Total Bookmarks:</strong> {result['stats']['total_bookmarks']}</li>
                                        <li><strong>Modified Bookmarks:</strong> {result['stats']['bookmarks_with_changes']}</li>
                                        <li><strong>Processing Time:</strong> {result['stats']['processing_time']:.2f} seconds</li>
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Read output file for download
                                output_file_path = result['output_path']
                                
                                with open(output_file_path, 'rb') as f:
                                    pdf_data = f.read()
                                
                                # Generate filename with timestamp
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                download_filename = f"consolidated_ecrf_{timestamp}.pdf"
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download Consolidated PDF",
                                    data=pdf_data,
                                    file_name=download_filename,
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True
                                )
                                
                                st.balloons()
                            else:
                                st.markdown(f"""
                                <div class="error-box">
                                    <h4>❌ Error</h4>
                                    <p>{result['error']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.markdown(f"""
                <div class="error-box">
                    <h4>❌ Error occurred during processing</h4>
                    <p>{str(e)}</p>
                </div>
                """, unsafe_allow_html=True)
                st.exception(e)
            
            finally:
                # Cleanup temporary directory
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    else:
        # Show placeholder when no file uploaded
        st.info("👆 Please upload a ZIP file to begin")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>eCRF PDF Consolidation Tool | Version 1.0 | © 2025</p>
</div>
""", unsafe_allow_html=True)
