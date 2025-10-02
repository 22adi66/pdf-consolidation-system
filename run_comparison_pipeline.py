"""
PDF Comparison Pipeline
========================
This module connects the PDF sequencer with the user's core comparison engine.
It runs comparisons on all PDF pairs and displays results after each comparison.
"""

from pdf_sequencer import PDFSequencer
from comparison_engine_core import compare_pdfs_advanced
import time
from datetime import datetime


class ComparisonPipeline:
    """
    Pipeline that orchestrates the comparison of multiple PDF versions.
    Uses the user's proven 3-pass comparison algorithm.
    """
    
    def __init__(self, input_directory: str, 
                 heuristic_threshold: float = 0.5,
                 global_threshold: float = 0.6,
                 show_identical: bool = False):
        """
        Initialize the comparison pipeline.
        
        Args:
            input_directory: Directory containing PDF files
            heuristic_threshold: Threshold for heuristic matching (0.0-1.0)
            global_threshold: Threshold for global matching (0.0-1.0)
            show_identical: Whether to show identical pages in report
        """
        self.input_directory = input_directory
        self.heuristic_threshold = heuristic_threshold
        self.global_threshold = global_threshold
        self.show_identical = show_identical
        self.sequencer = PDFSequencer(input_directory)
        self.comparison_results = []
    
    def run(self) -> list:
        """
        Run the complete comparison pipeline.
        
        Returns:
            List of comparison results for each pair
        """
        print("\n" + "🚀" * 50)
        print("PDF COMPARISON PIPELINE - STARTING")
        print("🚀" * 50)
        print(f"\n📁 Input Directory: {self.input_directory}")
        print(f"⚙️  Heuristic Threshold: {self.heuristic_threshold}")
        print(f"⚙️  Global Threshold: {self.global_threshold}")
        print(f"⚙️  Show Identical Pages: {self.show_identical}")
        print()
        
        # Scan directory for PDFs
        print("🔍 Step 1: Scanning directory for PDF files...")
        self.sequencer.scan_directory()
        print(f"✅ Found {len(self.sequencer.pdf_files)} PDF files")
        print()
        
        # Create comparison pairs
        print("🔗 Step 2: Creating comparison pairs...")
        pairs = self.sequencer.create_comparison_pairs()
        print(f"✅ Created {len(pairs)} comparison pairs")
        print()
        
        # Display sequence information
        self.sequencer.print_sequence_info()
        
        # Run comparisons
        print("\n" + "📊" * 50)
        print("STARTING SEQUENTIAL COMPARISONS")
        print("📊" * 50)
        print()
        
        self.comparison_results = []
        
        for pair_num, (pdf1, pdf2) in enumerate(pairs, 1):
            print("\n" + "═" * 100)
            print(f"{'COMPARISON PAIR #{}'.format(pair_num):^100}")
            print("═" * 100)
            print(f"LEFT:  v{pdf1.version_string} - {pdf1.filename}")
            print(f"RIGHT: v{pdf2.version_string} - {pdf2.filename}")
            print("═" * 100)
            print()
            
            start_time = time.time()
            
            # Run comparison using user's core engine
            result = compare_pdfs_advanced(
                file1_path=pdf1.filepath,
                file2_path=pdf2.filepath,
                heuristic_threshold=self.heuristic_threshold,
                global_threshold=self.global_threshold,
                show_identical=self.show_identical
            )
            
            elapsed = time.time() - start_time
            
            # Store result with metadata
            comparison_data = {
                'pair_number': pair_num,
                'pdf1': pdf1,
                'pdf2': pdf2,
                'result': result,
                'elapsed_time': elapsed,
                'timestamp': datetime.now()
            }
            self.comparison_results.append(comparison_data)
            
            # Print summary for this comparison
            print()
            print("─" * 100)
            print(f"⏱️  Comparison completed in {elapsed:.2f} seconds")
            
            if result:
                total_matches = len(result['matches'])
                identical_matches = len([m for m in result['matches'] if m[2] == 1.0])
                modified_matches = total_matches - identical_matches
                added_pages = len(result['unmatched2'])
                deleted_pages = len(result['unmatched1'])
                
                print(f"📊 Summary for Pair #{pair_num}:")
                print(f"   ✅ Total Matches: {total_matches}")
                print(f"   🔄 Identical Pages: {identical_matches}")
                print(f"   📝 Modified Pages: {modified_matches}")
                print(f"   ➕ Added Pages: {added_pages}")
                print(f"   ➖ Deleted Pages: {deleted_pages}")
            else:
                print(f"⚠️  Comparison failed or returned no results")
            
            print("─" * 100)
            print()
        
        # Print final summary
        self._print_final_summary()
        
        return self.comparison_results
    
    def _print_final_summary(self):
        """Print a final summary of all comparisons."""
        print("\n" + "🎯" * 50)
        print("FINAL SUMMARY - ALL COMPARISONS")
        print("🎯" * 50)
        print()
        
        total_comparisons = len(self.comparison_results)
        total_time = sum(c['elapsed_time'] for c in self.comparison_results)
        
        print(f"📊 Total Comparisons: {total_comparisons}")
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        print(f"⌛ Average Time per Comparison: {total_time/total_comparisons:.2f} seconds")
        print()
        
        # Aggregate statistics
        total_matches = 0
        total_modified = 0
        total_added = 0
        total_deleted = 0
        
        for comp in self.comparison_results:
            if comp['result']:
                result = comp['result']
                matches = result['matches']
                total_matches += len(matches)
                total_modified += len([m for m in matches if m[2] < 1.0])
                total_added += len(result['unmatched2'])
                total_deleted += len(result['unmatched1'])
        
        print("📈 Aggregate Statistics:")
        print(f"   🔄 Total Page Matches: {total_matches}")
        print(f"   📝 Total Modified Pages: {total_modified}")
        print(f"   ➕ Total Added Pages: {total_added}")
        print(f"   ➖ Total Deleted Pages: {total_deleted}")
        print()
        
        print("✅ COMPARISON PIPELINE COMPLETED SUCCESSFULLY!")
        print("🎯" * 50)
        print()
    
    def get_results(self) -> list:
        """Get all comparison results."""
        return self.comparison_results
    
    def export_summary(self, output_file: str = "comparison_summary.txt"):
        """Export a text summary of all comparisons."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PDF COMPARISON PIPELINE - SUMMARY REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input Directory: {self.input_directory}\n")
            f.write(f"Total Comparisons: {len(self.comparison_results)}\n")
            f.write("=" * 80 + "\n\n")
            
            for comp in self.comparison_results:
                pair_num = comp['pair_number']
                pdf1 = comp['pdf1']
                pdf2 = comp['pdf2']
                result = comp['result']
                elapsed = comp['elapsed_time']
                
                f.write(f"\nCOMPARISON PAIR #{pair_num}\n")
                f.write("-" * 80 + "\n")
                f.write(f"LEFT:  v{pdf1.version_string} - {pdf1.filename}\n")
                f.write(f"RIGHT: v{pdf2.version_string} - {pdf2.filename}\n")
                f.write(f"Time: {elapsed:.2f} seconds\n")
                
                if result:
                    matches = result['matches']
                    identical = len([m for m in matches if m[2] == 1.0])
                    modified = len(matches) - identical
                    added = len(result['unmatched2'])
                    deleted = len(result['unmatched1'])
                    
                    f.write(f"  - Total Matches: {len(matches)}\n")
                    f.write(f"  - Identical: {identical}\n")
                    f.write(f"  - Modified: {modified}\n")
                    f.write(f"  - Added: {added}\n")
                    f.write(f"  - Deleted: {deleted}\n")
                else:
                    f.write("  - Status: FAILED\n")
                
                f.write("-" * 80 + "\n")
        
        print(f"📄 Summary exported to: {output_file}")


def main():
    """Main function to run the comparison pipeline."""
    # Configuration
    INPUT_DIR = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    HEURISTIC_THRESHOLD = 0.5
    GLOBAL_THRESHOLD = 0.6
    SHOW_IDENTICAL = False
    
    # Create and run pipeline
    pipeline = ComparisonPipeline(
        input_directory=INPUT_DIR,
        heuristic_threshold=HEURISTIC_THRESHOLD,
        global_threshold=GLOBAL_THRESHOLD,
        show_identical=SHOW_IDENTICAL
    )
    
    # Run all comparisons
    results = pipeline.run()
    
    # Export summary
    pipeline.export_summary("comparison_summary.txt")
    
    return pipeline, results


if __name__ == "__main__":
    pipeline, results = main()
