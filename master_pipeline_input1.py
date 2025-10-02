"""
Master Pipeline for INPUT1
===========================
Runs the complete PDF consolidation pipeline on INPUT1 directory.
"""

import os
import time
from pdf_sequencer import PDFSequencer
from pdf_consolidator import PDFConsolidator
from comparison_engine_core import compare_pdfs_advanced


class MasterConsolidationPipeline:
    """
    Master orchestrator for the complete PDF consolidation workflow.
    """
    
    def __init__(self, input_dir: str, output_pdf: str, 
                 heuristic_threshold: float = 0.5, 
                 global_threshold: float = 0.6):
        """
        Initialize the master pipeline.
        
        Args:
            input_dir: Directory containing input PDF files
            output_pdf: Path for the consolidated output PDF
            heuristic_threshold: Threshold for heuristic matching
            global_threshold: Threshold for global optimal matching
        """
        self.input_dir = input_dir
        self.output_pdf = output_pdf
        self.heuristic_threshold = heuristic_threshold
        self.global_threshold = global_threshold
        
        # Statistics
        self.total_comparisons = 0
        self.total_pdfs = 0
        self.modified_pages_count = 0
        self.added_pages_count = 0
        self.deleted_pages_count = 0
        self.pipeline_start_time = None
    
    def run(self):
        """Execute the complete consolidation pipeline."""
        self.pipeline_start_time = time.time()
        
        print("\n" + "🚀" * 50)
        print("MASTER PDF CONSOLIDATION PIPELINE - INPUT1")
        print("🚀" * 50)
        print()
        
        # ====================================================================
        # PHASE 1: ANALYZE & SEQUENCE PDFs
        # ====================================================================
        print("=" * 80)
        print("PHASE 1: PDF SEQUENCING & VERSION ANALYSIS")
        print("=" * 80)
        print()
        
        self.sequencer = PDFSequencer(self.input_dir)
        self.sequencer.analyze_directory()
        
        if not self.sequencer.pdf_files:
            print("❌ No PDF files found in input directory!")
            return
        
        self.total_pdfs = len(self.sequencer.pdf_files)
        
        print()
        print("=" * 80)
        print("✅ SEQUENCE ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        
        # ====================================================================
        # PHASE 2: INITIALIZE CONSOLIDATOR
        # ====================================================================
        print()
        print("=" * 80)
        print("PHASE 2: INITIALIZE CONSOLIDATOR")
        print("=" * 80)
        print()
        
        # Get base PDF (oldest version)
        base_pdf_version = self.sequencer.get_base_pdf()
        
        # Initialize consolidator
        self.consolidator = PDFConsolidator(
            base_pdf_path=base_pdf_version.filepath,
            output_path=self.output_pdf
        )
        
        # Initialize with base PDF
        self.consolidator.initialize_base_pdf()
        
        # ====================================================================
        # PHASE 3: SEQUENTIAL COMPARISONS & CONSOLIDATION
        # ====================================================================
        print()
        print("=" * 80)
        print("PHASE 3: SEQUENTIAL COMPARISONS & CONSOLIDATION")
        print("=" * 80)
        print()
        
        comparison_pairs = self.sequencer.get_comparison_pairs()
        self.total_comparisons = len(comparison_pairs)
        
        for idx, (left_pdf, right_pdf) in enumerate(comparison_pairs, 1):
            print("─" * 80)
            print(f"PROCESSING PAIR #{idx}/{self.total_comparisons}")
            print("─" * 80)
            print(f"LEFT:  {left_pdf.version_string} - {left_pdf.filename}")
            print(f"RIGHT: {right_pdf.version_string} - {right_pdf.filename}")
            print("─" * 80)
            print()
            
            # Run comparison
            comparison_result = compare_pdfs_advanced(
                left_pdf.filepath,
                right_pdf.filepath,
                heuristic_threshold=self.heuristic_threshold,
                global_threshold=self.global_threshold
            )
            
            # Track statistics
            if comparison_result:
                self.modified_pages_count += len(comparison_result.get('matched_modified', []))
                self.added_pages_count += len(comparison_result.get('unmatched2', []))
                self.deleted_pages_count += len(comparison_result.get('unmatched1', []))
            
            # Insert changes into consolidated PDF
            if comparison_result and (comparison_result.get('matched_modified') or 
                                     comparison_result.get('unmatched2')):
                self.consolidator.insert_modified_pages(
                    comparison_result,
                    right_pdf.filepath,
                    right_pdf.version_string
                )
            else:
                print(f"   ℹ️  No changes detected - skipping insertion")
            
            print()
        
        # ====================================================================
        # PHASE 4: BUILD BOOKMARK HIERARCHY
        # ====================================================================
        print()
        print("=" * 80)
        print("PHASE 4: BUILD BOOKMARK HIERARCHY")
        print("=" * 80)
        print()
        
        self.consolidator.build_bookmark_hierarchy()
        
        # ====================================================================
        # PHASE 5: SAVE CONSOLIDATED PDF
        # ====================================================================
        print()
        print("=" * 80)
        print("PHASE 5: SAVE CONSOLIDATED PDF")
        print("=" * 80)
        print()
        
        self.consolidator.save()
        
        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        self.print_summary()
    
    def print_summary(self):
        """Print comprehensive pipeline summary."""
        pipeline_time = time.time() - self.pipeline_start_time
        
        print()
        print("🎯" * 50)
        print("FINAL PIPELINE SUMMARY")
        print("🎯" * 50)
        print()
        print(f"⏱️  Total Pipeline Time: {pipeline_time:.2f} seconds ({pipeline_time/60:.2f} minutes)")
        print(f"📊 Total Comparisons: {self.total_comparisons}")
        print(f"📄 Total PDFs Processed: {self.total_pdfs}")
        print()
        print(f"📈 Change Statistics:")
        print(f"   Modified Pages: {self.modified_pages_count}")
        print(f"   Added Pages: {self.added_pages_count}")
        print(f"   Deleted Pages: {self.deleted_pages_count}")
        print()
        
        # Print consolidator's detailed summary
        self.consolidator.print_summary()
        
        print("✅ MASTER PIPELINE COMPLETED SUCCESSFULLY!")
        print("🎯" * 50)


def main():
    """Main entry point."""
    # Configuration
    INPUT_DIR = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    OUTPUT_DIR = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\OUTPUT"
    OUTPUT_PDF = os.path.join(OUTPUT_DIR, "input1_output.pdf")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create and run pipeline
    pipeline = MasterConsolidationPipeline(
        input_dir=INPUT_DIR,
        output_pdf=OUTPUT_PDF,
        heuristic_threshold=0.5,
        global_threshold=0.6
    )
    
    pipeline.run()


if __name__ == "__main__":
    main()
