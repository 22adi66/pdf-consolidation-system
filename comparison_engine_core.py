"""
Core Comparison Engine - User's Original Code
==============================================
This is the user's original comparison logic with the 3-pass strategy.
DO NOT MODIFY THIS FILE - It contains the proven comparison algorithm.
"""

import PyPDF2
import difflib
import re
from collections import defaultdict
from bisect import bisect_left

# --- Text Processing and PDF Extraction ---

def sanitize_text(text: str) -> str:
    """Removes volatile text like page numbers, version info, etc."""
    patterns_to_remove = [
        r'Form Version:.*',                  # remove 'Form Version: ...'
        r'Generated Time \(GMT\):.*',        # remove 'Generated Time (GMT): ...'
        r'\\Confidential\\',                 # escaped Confidential markers
        r'Page \d+ of \d+'                   # remove 'Page X of Y'
    ]
    sanitized_text = text or ""
    for pattern in patterns_to_remove:
        sanitized_text = re.sub(pattern, '', sanitized_text, flags=re.IGNORECASE | re.MULTILINE)
    # collapse multiple blank lines and strip
    sanitized_text = re.sub(r'\n\s*\n+', '\n\n', sanitized_text).strip()
    return sanitized_text

def extract_text_by_page(pdf_reader: PyPDF2.PdfReader) -> list:
    """Extracts and sanitizes text from each page of a PDF."""
    pages_text = []
    for page in pdf_reader.pages:
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            # fallback if extract_text fails for a page
            raw_text = ""
        pages_text.append(sanitize_text(raw_text))
    return pages_text

def get_form_name(page_text: str) -> str:
    """Parses the 'Form: ...' line from the page text."""
    if not page_text:
        return ""
    match = re.search(r"Form:\s*(.*?)\s*$", page_text, re.MULTILINE)
    return match.group(1).strip() if match else ""

def create_page_to_bookmark_map(pdf_reader: PyPDF2.PdfReader) -> list:
    """
    Creates a map from page number (1-indexed) to its corresponding bookmark title.
    Returns a list where index == page number and element is bookmark title (index 0 unused).
    """
    total_pages = len(pdf_reader.pages)
    # prepare map with (total_pages + 1) entries, index 0 unused for convenience
    page_map = ["(No Bookmark)"] * (total_pages + 1)

    # Get outlines using the modern .outline attribute
    outlines = None
    try:
        # PyPDF2 v3.0.0+ uses the .outline attribute
        outlines = pdf_reader.outline
    except Exception:
        # This block can be extended for older version fallbacks if needed,
        # but for now, it just ensures the code doesn't crash.
        outlines = None

    if not outlines:
        # no bookmarks/outlines found
        return page_map

    bookmark_pages = []

    def _traverse_bookmarks(items):
        for item in items:
            # nested list indicates children
            if isinstance(item, list):
                _traverse_bookmarks(item)
                continue

            # try to extract title
            title = getattr(item, "title", None) or getattr(item, "name", None) or str(item)

            # try different ways to get page number
            page_num = None
            try:
                # many PyPDF2 versions: Destination-like objects have .page attribute
                page_obj = getattr(item, "page", None)
                if page_obj is not None:
                    page_num = pdf_reader.get_page_number(page_obj) + 1
                else:
                    # some versions allow get_destination_page_number
                    if hasattr(pdf_reader, "get_destination_page_number"):
                        try:
                            page_num = pdf_reader.get_destination_page_number(item) + 1
                        except Exception:
                            page_num = None
            except Exception:
                page_num = None

            # last resort: some bookmark items have /Page entry in raw dict
            if page_num is None:
                try:
                    # item might be a dict-like object
                    raw = getattr(item, "object", None) or item
                    if isinstance(raw, dict):
                        # try standard keys
                        dest = raw.get("/A") or raw.get("/Dest") or raw.get("A") or raw.get("Dest")
                        # we don't go deep; simply ignore if cannot derive
                except Exception:
                    pass

            if page_num is not None:
                bookmark_pages.append((page_num, str(title)))

    try:
        _traverse_bookmarks(outlines)
    except Exception:
        # If traversal failed, return default map
        return page_map

    if not bookmark_pages:
        return page_map

    # sort by page number and fill page_map with the nearest preceding bookmark title
    bookmark_pages.sort()
    current_title = bookmark_pages[0][1]
    idx = 0
    for page in range(1, total_pages + 1):
        # advance bookmark index if we reach its start page
        while idx < len(bookmark_pages) and page >= bookmark_pages[idx][0]:
            current_title = bookmark_pages[idx][1]
            idx += 1
        page_map[page] = current_title

    return page_map

# --- Similarity and Advanced Mapping ---

def calculate_sequence_similarity(text1: str, text2: str) -> float:
    """Line-based SequenceMatcher ratio (0.0 - 1.0)."""
    return difflib.SequenceMatcher(None, (text1 or "").splitlines(), (text2 or "").splitlines()).ratio()

def find_longest_non_crossing_subsequence(matches: list) -> set:
    """
    Given list of (i, j) pairs, return a maximal set of non-crossing pairs
    (i increasing and j increasing) using an LIS on j after sorting by i.
    Returns a set of (i,j) tuples that form the LIS.
    """
    if not matches:
        return set()

    # sort by i (then by j)
    pairs = sorted(matches, key=lambda x: (x[0], x[1]))
    js = [p[1] for p in pairs]

    # standard patience-LIS to get indices
    tails = []          # stores tail values
    tails_idx = []      # stores index in pairs of the tails
    prev = [-1] * len(js) # predecessor indices

    for i, val in enumerate(js):
        pos = bisect_left(tails, val)
        if pos == len(tails):
            tails.append(val)
            tails_idx.append(i)
        else:
            tails[pos] = val
            tails_idx[pos] = i
        if pos > 0:
            prev[i] = tails_idx[pos - 1]

    # reconstruct LIS indices
    lis_indices = []
    k = tails_idx[-1]
    while k != -1:
        lis_indices.append(k)
        k = prev[k]
    lis_indices.reverse()

    result = {pairs[idx] for idx in lis_indices}
    return result

def find_optimal_mapping(pages1: dict, pages2: dict) -> list:
    """
    Global optimal mapping using dynamic programming similar to sequence alignment.
    pages1 and pages2 are dicts keyed by page indices (0-based) -> text.
    Returns list of (i, j, score) in increasing order.
    """
    indices1, indices2 = sorted(pages1.keys()), sorted(pages2.keys())
    len1, len2 = len(indices1), len(indices2)
    if len1 == 0 or len2 == 0:
        return []

    # build similarity matrix
    sim_matrix = [[calculate_sequence_similarity(pages1[i1], pages2[i2]) for i2 in indices2] for i1 in indices1]

    # DP table
    dp = [[0.0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            match_score = dp[i - 1][j - 1] + sim_matrix[i - 1][j - 1]
            dp[i][j] = max(match_score, dp[i - 1][j], dp[i][j - 1])

    # backtrack to collect matches
    matches = []
    i, j = len1, len2
    while i > 0 and j > 0:
        current_score = dp[i][j]
        match_score = dp[i - 1][j - 1] + sim_matrix[i - 1][j - 1]
        if abs(current_score - match_score) < 1e-9:
            matches.append((indices1[i - 1], indices2[j - 1], sim_matrix[i - 1][j - 1]))
            i, j = i - 1, j - 1
        elif abs(current_score - dp[i - 1][j]) < 1e-9:
            i -= 1
        else:
            j -= 1

    matches.reverse()
    return matches

# --- Main Comparison Logic with Improved 3-Pass Strategy ---
def run_comparison_on_text(pages1_text, pages2_text, bookmark_map1, bookmark_map2, file1_name, file2_name,
                           heuristic_threshold=0.5, global_threshold=0.6, show_identical=False):
    matches = []
    unmatched1 = set(range(len(pages1_text)))
    unmatched2 = set(range(len(pages2_text)))
    
    # --- Pass 1: Identical Match & De-crossing ---
    print("Pass 1: Finding 100% identical pages and de-crossing...")
    identical_matches_raw = []
    content_map2 = defaultdict(list)
    for j in unmatched2:
        content_map2[pages2_text[j]].append(j)
    
    for i in list(unmatched1):
        text1 = pages1_text[i]
        if text1 in content_map2 and content_map2[text1]:
            j = content_map2[text1].pop(0)
            identical_matches_raw.append((i, j))

    non_crossing_set = find_longest_non_crossing_subsequence(identical_matches_raw)
    
    for i, j in identical_matches_raw:
        if (i, j) in non_crossing_set:
            matches.append((i, j, 1.0))
            unmatched1.discard(i)
            unmatched2.discard(j)
    print(f"Pass 1 complete. Found {len([m for m in matches if m[2] == 1.0])} non-crossing identical matches.")
    
    # --- Pass 2: Heuristic Match (Bookmark + Form Name + Local Proximity Window) ---
    print("\nPass 2: Finding matches by Bookmark + Form Name + Local Proximity...")
    pass2_matches_count = 0
    
    form_names1 = {i: get_form_name(pages1_text[i]) for i in unmatched1}
    form_names2 = {j: get_form_name(pages2_text[j]) for j in unmatched2}
    
    proximity_window = 2 # Check +/- 2 pages
    for i in list(unmatched1):
        bookmark1 = bookmark_map1[i + 1] if (i + 1) < len(bookmark_map1) else ""
        form_name1 = form_names1.get(i, "")
        if not bookmark1 or not form_name1:
            continue
        
        local_candidates = []
        start_j = max(0, i - proximity_window)
        end_j = min(len(pages2_text), i + proximity_window + 1)
        
        for j in range(start_j, end_j):
            if j in unmatched2:
                bookmark2 = bookmark_map2[j + 1] if (j + 1) < len(bookmark_map2) else ""
                form_name2 = form_names2.get(j, "")
                
                if bookmark2 and form_name2:
                    bookmark_match = (bookmark1 in bookmark2) or (bookmark2 in bookmark1) or (bookmark1 == bookmark2)
                    form_name_match = (form_name1 in form_name2) or (form_name2 in form_name1) or (form_name1 == form_name2)
                    
                    if bookmark_match and form_name_match:
                        score = calculate_sequence_similarity(pages1_text[i], pages2_text[j])
                        if score >= heuristic_threshold:
                            local_candidates.append((score, j))
        
        if local_candidates:
            best_score, best_j = max(local_candidates)
            matches.append((i, best_j, best_score))
            unmatched1.discard(i)
            unmatched2.discard(best_j)
            pass2_matches_count += 1

    print(f"Pass 2 complete. Found {pass2_matches_count} heuristic matches.")

    # --- Pass 3: Global Optimal Mapping (Safety Net) ---
    print("\nPass 3: Running global analysis on remaining pages...")
    pass3_matches_count = 0
    if unmatched1 and unmatched2:
        remaining_pages1 = {i: pages1_text[i] for i in unmatched1}
        remaining_pages2 = {j: pages2_text[j] for j in unmatched2}
        optimal_matches = find_optimal_mapping(remaining_pages1, remaining_pages2)
        for i, j, score in optimal_matches:
            if score >= global_threshold:
                matches.append((i, j, score))
                pass3_matches_count += 1
                unmatched1.discard(i)
                unmatched2.discard(j)
    print(f"Pass 3 complete. Found {pass3_matches_count} matches.")

    # --- Reporting Logic ---
    
    # Helper function to get all pages for a bookmark
    def get_pages_for_bookmark(bookmark_title, bookmark_map):
        """Get all page numbers that belong to a specific bookmark."""
        pages = []
        for page_num in range(1, len(bookmark_map)):
            if bookmark_map[page_num] == bookmark_title:
                pages.append(page_num)
        return pages
    
    print("\n\n" + "="*50 + "\nCOMPARISON REPORT\n" + "="*50 + "\n")
    if matches:
        print("--- Matched & Modified Pages ---\n")
        matches.sort()
        for i, j, score in matches:
            page1_num, page2_num = i + 1, j + 1
            bookmark1 = bookmark_map1[page1_num] if page1_num < len(bookmark_map1) else "(No Bookmark)"
            bookmark2 = bookmark_map2[page2_num] if page2_num < len(bookmark_map2) else "(No Bookmark)"
            if score == 1.0:
                if show_identical:
                    print(f"IDENTICAL: Page {page1_num} & Page {page2_num}. Bookmark: '{bookmark1}'\n" + "-"*25)
            else:
                print(f"MODIFIED: Page {page1_num} & Page {page2_num} (Similarity: {score:.1%})")
                print(f"  📑 Bookmark (File 1): '{bookmark1}'")
                
                # Get all pages for this bookmark in File 1
                bookmark1_pages = get_pages_for_bookmark(bookmark1, bookmark_map1)
                if bookmark1_pages:
                    print(f"     All pages in this bookmark (File 1): {', '.join(map(str, bookmark1_pages))}")
                
                if bookmark1 != bookmark2:
                    print(f"  📑 Bookmark (File 2): '{bookmark2}'")
                    # Get all pages for this bookmark in File 2
                    bookmark2_pages = get_pages_for_bookmark(bookmark2, bookmark_map2)
                    if bookmark2_pages:
                        print(f"     All pages in this bookmark (File 2): {', '.join(map(str, bookmark2_pages))}")
                
                diff = difflib.unified_diff(
                    (pages1_text[i] or "").splitlines(),
                    (pages2_text[j] or "").splitlines(),
                    fromfile=f'File1_Page{page1_num}',
                    tofile=f'File2_Page{page2_num}',
                    lineterm=''
                )
                for line in diff:
                    print(f"    {line}")
                print("-" * 25)
    
    deleted_pages = sorted(list(unmatched1))
    if deleted_pages:
        print(f"\n--- Deleted Pages ---\nPages from '{file1_name}' not in '{file2_name}':")
        deleted_by_bookmark = defaultdict(list)
        for p_idx in deleted_pages:
            p_num = p_idx + 1
            bookmark = bookmark_map1[p_num] if p_num < len(bookmark_map1) else "(No Bookmark)"
            deleted_by_bookmark[bookmark].append(p_num)
        
        for bookmark, pages in deleted_by_bookmark.items():
            # Get all pages for this bookmark in the source file
            all_bookmark_pages = get_pages_for_bookmark(bookmark, bookmark_map1)
            print(f"  📑 Bookmark: '{bookmark}'")
            print(f"     Deleted Pages: {', '.join(map(str, pages))}")
            print(f"     All Pages in Bookmark (File 1): {', '.join(map(str, all_bookmark_pages))}")
            print()
    
    added_pages = sorted(list(unmatched2))
    if added_pages:
        print(f"\n--- Added Pages ---\nPages from '{file2_name}' not in '{file1_name}':")
        added_by_bookmark = defaultdict(list)
        for p_idx in added_pages:
            p_num = p_idx + 1
            bookmark = bookmark_map2[p_num] if p_num < len(bookmark_map2) else "(No Bookmark)"
            added_by_bookmark[bookmark].append(p_num)
        
        for bookmark, pages in added_by_bookmark.items():
            # Get all pages for this bookmark in the target file
            all_bookmark_pages = get_pages_for_bookmark(bookmark, bookmark_map2)
            print(f"  📑 Bookmark: '{bookmark}'")
            print(f"     Added Pages: {', '.join(map(str, pages))}")
            print(f"     All Pages in Bookmark (File 2): {', '.join(map(str, all_bookmark_pages))}")
            print()

    # --- Version Tracking Summary ---
    print("\n" + "="*50 + "\nVERSION TRACKING SUMMARY\n" + "="*50 + "\n")
    
    # Collect bookmarks that will need new versions
    bookmarks_needing_versions = defaultdict(list)
    
    # Modified pages will create new versions
    for i, j, score in matches:
        if score < 1.0:  # Only non-identical pages need versioning
            page1_num = i + 1
            bookmark1 = bookmark_map1[page1_num] if page1_num < len(bookmark_map1) else "(No Bookmark)"
            bookmarks_needing_versions[bookmark1].append(('modified', page1_num))
    
    # Added pages will create new versions
    for p_idx in sorted(list(unmatched2)):
        p_num = p_idx + 1
        bookmark2 = bookmark_map2[p_num] if p_num < len(bookmark_map2) else "(No Bookmark)"
        bookmarks_needing_versions[bookmark2].append(('added', p_num))
    
    if bookmarks_needing_versions:
        print("📋 Bookmarks that will get NEW VERSION child bookmarks:\n")
        
        version_counter = {}
        for bookmark in sorted(bookmarks_needing_versions.keys()):
            # Determine version number (this will be calculated properly in consolidation)
            # For now, we show that a new version will be created
            pages_info = bookmarks_needing_versions[bookmark]
            modified_pages = [p for t, p in pages_info if t == 'modified']
            added_pages = [p for t, p in pages_info if t == 'added']
            
            print(f"  📑 Bookmark: '{bookmark}'")
            print(f"     ➕ New version will be added as child bookmark")
            print(f"     📄 Changes detected on pages: ", end="")
            
            all_pages = modified_pages + added_pages
            print(', '.join(map(str, sorted(all_pages))))
            
            if modified_pages and added_pages:
                print(f"        (Modified: {', '.join(map(str, sorted(modified_pages)))} | Added: {', '.join(map(str, sorted(added_pages)))})")
            elif modified_pages:
                print(f"        (Modified pages)")
            elif added_pages:
                print(f"        (Added pages)")
            
            print(f"     🏷️  Version Label: 'Version 2' (or next available version number)")
            print()
    else:
        print("✨ No new versions needed - all pages are identical!\n")
    
    print("="*50 + "\n")
    
    # Return structured data for downstream processing
    return {
        'matches': matches,
        'unmatched1': sorted(list(unmatched1)),
        'unmatched2': sorted(list(unmatched2)),
        'bookmark_map1': bookmark_map1,
        'bookmark_map2': bookmark_map2,
        'bookmarks_needing_versions': dict(bookmarks_needing_versions)
    }

def compare_pdfs_advanced(file1_path, file2_path, heuristic_threshold=0.5, global_threshold=0.6, show_identical=False):
    """Wrapper function to compare two PDF files from their paths."""
    print("\n" + "="*50 + f"\nStarting Comparison of '{file1_path}' and '{file2_path}'\n" + "="*50 + "\n")
    try:
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            reader1, reader2 = PyPDF2.PdfReader(f1), PyPDF2.PdfReader(f2)
            pages1_text = extract_text_by_page(reader1)
            bookmark_map1 = create_page_to_bookmark_map(reader1)
            pages2_text = extract_text_by_page(reader2)
            bookmark_map2 = create_page_to_bookmark_map(reader2)
    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e.filename}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        return None

    return run_comparison_on_text(
        pages1_text, pages2_text, bookmark_map1, bookmark_map2, file1_path, file2_path, 
        heuristic_threshold, global_threshold, show_identical
    )
