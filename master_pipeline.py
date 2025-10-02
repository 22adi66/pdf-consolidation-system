"""
Complete PDF Consolidation Pipeline
====================================
This module orchestrates the entire process:
1. Sequence PDFs by version
2. Run comparisons between consecutive versions
3. Build consolidated PDF with all versions tracked
"""

from pdf_sequencer import PDFSequencer
from comparison_engine_core import compare_pdfs_advanced
from pdf_consolidator import PDFConsolidator
import time
from datetime import datetime


class MasterConsolidationPipeline:
    """
    Master pipeline that coordinates sequencing, comparison, and consolidation.
    """
    
    def __init__(self, input_directory: str, output_pdf: str = "consolidated_final.pdf",
                 heuristic_threshold: float = 0.5, global_threshold: float = 0.6):
        """
        Initialize the master pipeline.
        
        Args:
            input_directory: Directory containing all PDF versions
            output_pdf: Path for final consolidated PDF
            heuristic_threshold: Threshold for heuristic matching
            global_threshold: Threshold for global matching
        """
        self.input_directory = input_directory
        self.output_pdf = output_pdf
        self.heuristic_threshold = heuristic_threshold
        self.global_threshold = global_threshold
        
        self.sequencer = None
        self.consolidator = None
        self.comparison_results = []
    
    def run(self):
        """Execute the complete consolidation pipeline."""
        print("\n" + "🚀" * 60)
        print("MASTER PDF CONSOLIDATION PIPELINE")
        print("🚀" * 60)
        print()
        print(f"📁 Input Directory: {self.input_directory}")
        print(f"📄 Output PDF: {self.output_pdf}")
        print(f"⚙️  Heuristic Threshold: {self.heuristic_threshold}")
        print(f"⚙️  Global Threshold: {self.global_threshold}")
        print()
        
        start_time = time.time()
        
        # Phase 1: Sequence PDFs
        print("\n" + "=" * 100)
        print("PHASE 1: PDF SEQUENCING & ANALYSIS")
        print("=" * 100)
        print()
        
        self.sequencer = PDFSequencer(self.input_directory)
        self.sequencer.scan_directory()
        pairs = self.sequencer.create_comparison_pairs()
        
        self.sequencer.print_sequence_info()
        
        base_pdf = self.sequencer.get_base_pdf()
        
        # Phase 2: Initialize Consolidator with Base PDF
        print("\n" + "=" * 100)
        print("PHASE 2: INITIALIZE CONSOLIDATOR")
        print("=" * 100)
        print()
        
        self.consolidator = PDFConsolidator(base_pdf.filepath, self.output_pdf)
        self.consolidator.initialize_base_pdf()
        
        # Phase 3: Run Comparisons and Insert Changes
        print("\n" + "=" * 100)
        print("PHASE 3: SEQUENTIAL COMPARISONS & CONSOLIDATION")
        print("=" * 100)
        print()
        
        for pair_num, (pdf1, pdf2) in enumerate(pairs, 1):
            print("\n" + "─" * 100)
            print(f"PROCESSING PAIR #{pair_num}/{len(pairs)}")
            print("─" * 100)
            print(f"LEFT:  v{pdf1.version_string} - {pdf1.filename}")
            print(f"RIGHT: v{pdf2.version_string} - {pdf2.filename}")
            print("─" * 100)
            print()
            
            comparison_start = time.time()
            
            # Run comparison
            result = compare_pdfs_advanced(
                file1_path=pdf1.filepath,
                file2_path=pdf2.filepath,
                heuristic_threshold=self.heuristic_threshold,
                global_threshold=self.global_threshold,
                show_identical=False
            )
            
            comparison_elapsed = time.time() - comparison_start
            
            # Store result
            self.comparison_results.append({
                'pair_number': pair_num,
                'pdf1': pdf1,
                'pdf2': pdf2,
                'result': result,
                'elapsed_time': comparison_elapsed
            })
            
            print(f"\n⏱️  Comparison completed in {comparison_elapsed:.2f} seconds")
            print()
            
            # Insert changes into consolidated PDF
            if result and result.get('bookmarks_needing_versions'):
                self.consolidator.insert_modified_pages(
                    comparison_result=result,
                    source_pdf_path=pdf2.filepath,
                    pdf_version=f"v{pdf2.version_string}"
                )
            else:
                print(f"   ℹ️  No changes detected - skipping insertion")
                print()
        
        # Phase 4: Build Bookmark Hierarchy
        print("\n" + "=" * 100)
        print("PHASE 4: BUILD BOOKMARK HIERARCHY")
        print("=" * 100)
        print()
        
        self.consolidator.build_bookmark_hierarchy()
        
        # Phase 5: Save Final PDF
        print("\n" + "=" * 100)
        print("PHASE 5: SAVE CONSOLIDATED PDF")
        print("=" * 100)
        print()
        
        self.consolidator.save()
        
        # Final Summary
        total_elapsed = time.time() - start_time
        
        print("\n" + "🎯" * 60)
        print("FINAL PIPELINE SUMMARY")
        print("🎯" * 60)
        print()
        
        print(f"⏱️  Total Pipeline Time: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
        print(f"📊 Total Comparisons: {len(pairs)}")
        print(f"📄 Total PDFs Processed: {len(pairs) + 1}")
        print()
        
        # Comparison statistics
        total_modified = sum(len([m for m in c['result']['matches'] if m[2] < 1.0]) 
                            for c in self.comparison_results if c['result'])
        total_added = sum(len(c['result']['unmatched2']) 
                         for c in self.comparison_results if c['result'])
        total_deleted = sum(len(c['result']['unmatched1']) 
                           for c in self.comparison_results if c['result'])
        
        print("📈 Change Statistics:")
        print(f"   Modified Pages: {total_modified}")
        print(f"   Added Pages: {total_added}")
        print(f"   Deleted Pages: {total_deleted}")
        print()
        
        # Consolidator statistics
        self.consolidator.print_summary()
        
        print("✅ MASTER PIPELINE COMPLETED SUCCESSFULLY!")
        print("🎯" * 60)
        print()
        
        return self.consolidator


def main():
    """Main function to run the complete pipeline."""
    
    # Configuration
    INPUT_DIR = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    OUTPUT_PDF = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\OUTPUT\consolidated_final.pdf"
    
    # Create output directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
    
    # Run pipeline
    pipeline = MasterConsolidationPipeline(
        input_directory=INPUT_DIR,
        output_pdf=OUTPUT_PDF,
        heuristic_threshold=0.5,
        global_threshold=0.6
    )
    
    consolidator = pipeline.run()
    
    return pipeline, consolidator


if __name__ == "__main__":
    pipeline, consolidator = main()
