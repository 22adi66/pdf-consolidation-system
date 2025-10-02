"""
Test Pair #2 - Should have more changes
========================================
"""

from run_comparison_pipeline import ComparisonPipeline
from comparison_engine_core import compare_pdfs_advanced
import time

def test_pair_2():
    """Test the second comparison pair (v2.0.4 → v3.0.21)."""
    
    INPUT_DIR = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    
    # Create pipeline
    pipeline = ComparisonPipeline(
        input_directory=INPUT_DIR,
        heuristic_threshold=0.5,
        global_threshold=0.6,
        show_identical=False
    )
    
    # Scan and get pairs
    pipeline.sequencer.scan_directory()
    pairs = pipeline.sequencer.create_comparison_pairs()
    
    print("\n" + "🧪" * 50)
    print("TEST - COMPARISON PAIR #2 (Expected to have changes)")
    print("🧪" * 50)
    print()
    
    # Get the second pair
    pdf1, pdf2 = pairs[1]  # Index 1 = Pair #2
    
    print(f"Testing: v{pdf1.version_string} → v{pdf2.version_string}")
    print(f"LEFT:  {pdf1.filename}")
    print(f"RIGHT: {pdf2.filename}")
    print()
    
    start_time = time.time()
    
    result = compare_pdfs_advanced(
        file1_path=pdf1.filepath,
        file2_path=pdf2.filepath,
        heuristic_threshold=0.5,
        global_threshold=0.6,
        show_identical=False
    )
    
    elapsed = time.time() - start_time
    
    print()
    print("─" * 100)
    print(f"⏱️  Comparison completed in {elapsed:.2f} seconds")
    
    if result:
        matches = result['matches']
        identical = len([m for m in matches if m[2] == 1.0])
        modified = len(matches) - identical
        added = len(result['unmatched2'])
        deleted = len(result['unmatched1'])
        
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Total Page Matches: {len(matches)}")
        print(f"   🔄 Identical Pages: {identical}")
        print(f"   📝 Modified Pages: {modified}")
        print(f"   ➕ Added Pages: {added}")
        print(f"   ➖ Deleted Pages: {deleted}")
    else:
        print("\n⚠️  Comparison returned no results")
    
    print("─" * 100)
    print()
    print("✅ TEST COMPLETE!")
    print()
    
    return result


if __name__ == "__main__":
    result = test_pair_2()
