"""
Master Pipeline for INPUT2
===========================
Runs the complete PDF consolidation pipeline on INPUT2 directory.
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
        print("MASTER PDF CONSOLIDATION PIPELINE")
        print("🚀" * 50)
        print()
        print(f"📁 Input Directory: {self.input_dir}")
        print(f"📄 Output PDF: {self.output_pdf}")
        print(f"⚙️  Heuristic Threshold: {self.heuristic_threshold}")
        print(f"⚙️  Global Threshold: {self.global_threshold}")
        print()
        
        # Phase 1: PDF Sequencing & Analysis
        self._phase_1_sequencing()
        
        # Phase 2: Initialize Consolidator
        self._phase_2_initialize_consolidator()
        
        # Phase 3: Sequential Comparisons & Consolidation
        self._phase_3_sequential_comparisons()
        
        # Phase 4: Build Bookmark Hierarchy
        self._phase_4_build_hierarchy()
        
        # Phase 5: Save Final PDF
        self._phase_5_save_pdf()
        
        # Final Summary
        self._print_final_summary()
    
    def _phase_1_sequencing(self):
        """Phase 1: Analyze and sequence PDFs by version."""
        print("\n" + "=" * 80)
        print("PHASE 1: PDF SEQUENCING & ANALYSIS")
        print("=" * 80)
        print()
        
        self.sequencer = PDFSequencer(self.input_dir)
        self.sequencer.scan_directory()
        self.sequencer.sort_by_version()
        self.comparison_pairs = self.sequencer.create_comparison_pairs()
        self.sequencer.print_sequence_info()
        
        self.total_pdfs = len(self.sequencer.pdf_files)
        self.total_comparisons = len(self.comparison_pairs)
        
        print()
        print("=" * 80)
        print("✅ SEQUENCE ANALYSIS COMPLETE")
        print("=" * 80)
        print()
    
    def _phase_2_initialize_consolidator(self):
        """Phase 2: Initialize consolidator with base PDF."""
        print("\n" + "=" * 80)
        print("PHASE 2: INITIALIZE CONSOLIDATOR")
        print("=" * 80)
        print()
        
        # Get base PDF (oldest version - first in sorted sequence)
        base_pdf_version = self.sequencer.get_base_pdf()
        
        self.consolidator = PDFConsolidator(
            base_pdf_path=base_pdf_version.filepath,
            output_path=self.output_pdf
        )
        
        self.consolidator.initialize_base_pdf()
    
    def _phase_3_sequential_comparisons(self):
        """Phase 3: Run comparisons and consolidate changes."""
        print("\n" + "=" * 80)
        print("PHASE 3: SEQUENTIAL COMPARISONS & CONSOLIDATION")
        print("=" * 80)
        print()
        
        for idx, (left_pdf, right_pdf) in enumerate(self.comparison_pairs, 1):
            print("\n" + "─" * 80)
            print(f"PROCESSING PAIR #{idx}/{self.total_comparisons}")
            print("─" * 80)
            print(f"LEFT:  {left_pdf.version_string} - {left_pdf.filename}")
            print(f"RIGHT: {right_pdf.version_string} - {right_pdf.filename}")
            print("─" * 80)
            print()
            
            # Run comparison
            comparison_start = time.time()
            comparison_result = compare_pdfs_advanced(
                file1_path=left_pdf.filepath,
                file2_path=right_pdf.filepath,
                heuristic_threshold=self.heuristic_threshold,
                global_threshold=self.global_threshold,
                show_identical=False
            )
            comparison_time = time.time() - comparison_start
            
            print(f"\n⏱️  Comparison completed in {comparison_time:.2f} seconds")
            
            # Consolidate changes
            if comparison_result:
                matches = comparison_result.get('matches', [])
                has_changes = any(score < 1.0 for _, _, score in matches) or comparison_result.get('unmatched2', [])
                
                if has_changes:
                    self.consolidator.insert_modified_pages(
                        comparison_result=comparison_result,
                        source_pdf_path=right_pdf.filepath,
                        pdf_version=right_pdf.version_string
                    )
                    
                    # Update statistics
                    self.modified_pages_count += sum(1 for _, _, score in matches if score < 1.0)
                    self.added_pages_count += len(comparison_result.get('unmatched2', []))
                    self.deleted_pages_count += len(comparison_result.get('unmatched1', []))
                else:
                    print("   ℹ️  No changes detected - skipping insertion")
            
            print()
    
    def _phase_4_build_hierarchy(self):
        """Phase 4: Build bookmark hierarchy."""
        print("\n" + "=" * 80)
        print("PHASE 4: BUILD BOOKMARK HIERARCHY")
        print("=" * 80)
        print()
        
        self.consolidator.build_bookmark_hierarchy()
    
    def _phase_5_save_pdf(self):
        """Phase 5: Save the consolidated PDF."""
        print("\n" + "=" * 80)
        print("PHASE 5: SAVE CONSOLIDATED PDF")
        print("=" * 80)
        print()
        
        self.consolidator.save()
    
    def _print_final_summary(self):
        """Print final pipeline summary."""
        total_time = time.time() - self.pipeline_start_time
        
        print("\n" + "🎯" * 50)
        print("FINAL PIPELINE SUMMARY")
        print("🎯" * 50)
        print()
        print(f"⏱️  Total Pipeline Time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        print(f"📊 Total Comparisons: {self.total_comparisons}")
        print(f"📄 Total PDFs Processed: {self.total_pdfs}")
        print()
        print(f"📈 Change Statistics:")
        print(f"   Modified Pages: {self.modified_pages_count}")
        print(f"   Added Pages: {self.added_pages_count}")
        print(f"   Deleted Pages: {self.deleted_pages_count}")
        print()
        
        # Print consolidation summary
        self.consolidator.print_summary()
        
        print("✅ MASTER PIPELINE COMPLETED SUCCESSFULLY!")
        print("🎯" * 50)
        print()


def main():
    """Main entry point."""
    # Configuration
    input_directory = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT2"
    output_pdf = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\OUTPUT\consolidated_input2_final.pdf"
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    
    # Run pipeline
    pipeline = MasterConsolidationPipeline(
        input_dir=input_directory,
        output_pdf=output_pdf,
        heuristic_threshold=0.5,
        global_threshold=0.6
    )
    
    pipeline.run()


if __name__ == "__main__":
    main()
