"""
Backend Module for PDF Consolidation Pipeline
Provides a clean interface for the Streamlit frontend
"""

import os
import time
from typing import Dict, Any
from pathlib import Path
from pdf_sequencer import PDFSequencer
from comparison_engine_core import compare_pdfs_advanced
from pdf_consolidator import PDFConsolidator


class PDFConsolidationPipeline:
    """
    Main pipeline class that orchestrates the PDF consolidation process.
    """
    
    def __init__(self, input_dir: str, output_dir: str):
        """
        Initialize the pipeline.
        
        Args:
            input_dir: Directory containing PDF files to consolidate
            output_dir: Directory where output PDF will be saved
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.sequencer = None
        self.consolidator = None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete consolidation pipeline.
        
        Returns:
            Dictionary containing:
                - success: bool indicating if process succeeded
                - output_path: path to consolidated PDF (if successful)
                - stats: processing statistics
                - error: error message (if failed)
        """
        start_time = time.time()
        
        try:
            # Step 1: Analyze and sequence PDFs
            print("\n" + "=" * 80)
            print("PHASE 1: PDF SEQUENCING")
            print("=" * 80)
            
            self.sequencer = PDFSequencer(self.input_dir)
            self.sequencer.scan_directory()
            
            if len(self.sequencer.pdf_files) == 0:
                return {
                    'success': False,
                    'error': 'No PDF files found in the input directory'
                }
            
            if len(self.sequencer.pdf_files) < 2:
                return {
                    'success': False,
                    'error': 'Need at least 2 PDF files to perform consolidation'
                }
            
            # Get base PDF (oldest version)
            base_pdf_version = self.sequencer.get_base_pdf()
            base_pdf_path = base_pdf_version.filepath
            
            print(f"\n✅ Found {len(self.sequencer.pdf_files)} PDF files")
            print(f"📄 Base PDF: {base_pdf_version.filename} (v{base_pdf_version.version_string})")
            
            # Step 2: Initialize consolidator with base PDF
            print("\n" + "=" * 80)
            print("PHASE 2: INITIALIZE CONSOLIDATOR")
            print("=" * 80)
            
            output_filename = "consolidated_output.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            self.consolidator = PDFConsolidator(
                base_pdf_path=base_pdf_path,
                output_path=output_path
            )
            
            self.consolidator.initialize_base_pdf()
            
            # Step 3: Sequential comparisons and consolidation
            print("\n" + "=" * 80)
            print("PHASE 3: SEQUENTIAL COMPARISONS & CONSOLIDATION")
            print("=" * 80)
            
            comparison_pairs = self.sequencer.create_comparison_pairs()
            
            for idx, (left_version, right_version) in enumerate(comparison_pairs, 1):
                print("\n" + "─" * 80)
                print(f"PROCESSING PAIR #{idx}/{len(comparison_pairs)}")
                print("─" * 80)
                print(f"LEFT:  {left_version.version_string} - {left_version.filename}")
                print(f"RIGHT: {right_version.version_string} - {right_version.filename}")
                print("─" * 80)
                print()
                
                # Compare PDFs
                comparison_result = compare_pdfs_advanced(
                    left_version.filepath,
                    right_version.filepath
                )
                
                # Insert changes into consolidated PDF
                self.consolidator.insert_modified_pages(
                    comparison_result,
                    right_version.filepath,
                    right_version.version_string
                )
            
            # Step 4: Build bookmark hierarchy
            print("\n" + "=" * 80)
            print("PHASE 4: BUILD BOOKMARK HIERARCHY")
            print("=" * 80)
            
            self.consolidator.build_bookmark_hierarchy()
            
            # Step 5: Save consolidated PDF
            print("\n" + "=" * 80)
            print("PHASE 5: SAVE CONSOLIDATED PDF")
            print("=" * 80)
            
            self.consolidator.save()
            
            # Calculate statistics
            end_time = time.time()
            processing_time = end_time - start_time
            
            stats = {
                'total_pdfs': len(self.sequencer.pdf_files),
                'total_pages': self.consolidator.current_page_count,
                'total_bookmarks': len(self.consolidator.bookmark_trackers),
                'bookmarks_with_changes': len(self.consolidator.bookmarks_with_changes),
                'processing_time': processing_time
            }
            
            # Print summary
            print("\n" + "🎯" * 50)
            print("CONSOLIDATION COMPLETE")
            print("🎯" * 50)
            print()
            print(f"✅ Output saved to: {output_path}")
            print(f"📊 Total PDFs: {stats['total_pdfs']}")
            print(f"📄 Total Pages: {stats['total_pages']}")
            print(f"📑 Total Bookmarks: {stats['total_bookmarks']}")
            print(f"🔄 Bookmarks with Changes: {stats['bookmarks_with_changes']}")
            print(f"⏱️  Processing Time: {stats['processing_time']:.2f} seconds")
            print("=" * 80)
            
            return {
                'success': True,
                'output_path': output_path,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stats': {
                    'processing_time': time.time() - start_time
                }
            }


def run_pipeline_simple(input_dir: str, output_path: str) -> bool:
    """
    Simple wrapper function to run the pipeline.
    
    Args:
        input_dir: Directory containing PDF files
        output_path: Full path where output PDF should be saved
    
    Returns:
        True if successful, False otherwise
    """
    output_dir = os.path.dirname(output_path)
    
    pipeline = PDFConsolidationPipeline(input_dir, output_dir)
    result = pipeline.run()
    
    if result['success'] and output_path != result['output_path']:
        # Rename output file if needed
        import shutil
        shutil.move(result['output_path'], output_path)
        result['output_path'] = output_path
    
    return result['success']
