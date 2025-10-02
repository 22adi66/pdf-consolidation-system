"""
Quick Test - Single Pair Comparison
====================================
Test the pipeline with just the first comparison pair.
"""

from run_comparison_pipeline import ComparisonPipeline

def quick_test_single_pair():
    """Test with just the first comparison pair."""
    
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
    print("QUICK TEST - FIRST COMPARISON PAIR ONLY")
    print("🧪" * 50)
    print()
    
    # Get just the first pair
    pdf1, pdf2 = pairs[0]
    
    print(f"Testing: v{pdf1.version_string} → v{pdf2.version_string}")
    print()
    
    # Import and use the core comparison engine
    from comparison_engine_core import compare_pdfs_advanced
    import time
    
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
        
        print(f"\n📊 QUICK SUMMARY:")
        print(f"   ✅ Total Page Matches: {len(matches)}")
        print(f"   🔄 Identical Pages: {identical}")
        print(f"   📝 Modified Pages: {modified}")
        print(f"   ➕ Added Pages: {added}")
        print(f"   ➖ Deleted Pages: {deleted}")
    else:
        print("\n⚠️  Comparison returned no results")
    
    print("─" * 100)
    print()
    print("✅ QUICK TEST COMPLETE!")
    print()
    
    return result


if __name__ == "__main__":
    result = quick_test_single_pair()
