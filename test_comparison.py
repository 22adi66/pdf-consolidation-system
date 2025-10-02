"""
Quick Test - PDF Comparison
============================
This script does a quick test of one PDF comparison pair.
"""

from pdf_comparison_engine import PDFComparisonEngine
from pdf_sequencer import PDFSequencer
import time

def quick_test():
    """Quick test with just the first comparison pair."""
    
    # Create sequencer
    input_dir = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    sequencer = PDFSequencer(input_dir)
    
    print("🔍 Scanning directory...")
    sequencer.scan_directory()
    
    # Get comparison pairs
    pairs = sequencer.create_comparison_pairs()
    
    print(f"✅ Found {len(pairs)} comparison pairs\n")
    
    # Create comparison engine
    engine = PDFComparisonEngine(similarity_threshold=0.85)
    
    # Test with first pair only
    pdf1, pdf2 = pairs[0]
    
    print("=" * 100)
    print(f"🔍 TESTING COMPARISON - PAIR #1")
    print("=" * 100)
    print(f"LEFT:  {pdf1.filename} (v{pdf1.version_string})")
    print(f"RIGHT: {pdf2.filename} (v{pdf2.version_string})")
    print()
    print("⏳ Extracting text and comparing... (this may take a minute)")
    
    start_time = time.time()
    
    result = engine.compare(
        pdf1_path=pdf1.filepath,
        pdf2_path=pdf2.filepath,
        version1=f"v{pdf1.version_string}",
        version2=f"v{pdf2.version_string}"
    )
    
    elapsed = time.time() - start_time
    print(f"✅ Comparison completed in {elapsed:.2f} seconds")
    
    # Print results
    engine.print_comparison_result(result, pair_number=1)
    
    return result


if __name__ == "__main__":
    result = quick_test()
