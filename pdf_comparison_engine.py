"""
PDF Comparison Engine
=====================
This module compares two PDF files and detects changes in text, bookmarks, and structure.

It provides detailed comparison results including:
- Modified pages with diffs
- Added pages and sections
- Deleted pages and sections
- Bookmark changes
"""

import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher, unified_diff
import re


@dataclass
class PageInfo:
    """Information about a single page in a PDF."""
    page_number: int
    text: str
    bookmark: Optional[str] = None
    text_hash: Optional[str] = None
    
    def __post_init__(self):
        """Calculate hash after initialization."""
        if self.text_hash is None:
            # Normalize text for comparison (remove extra whitespace)
            normalized = ' '.join(self.text.split())
            self.text_hash = hash(normalized)


@dataclass
class BookmarkInfo:
    """Information about a bookmark in a PDF."""
    title: str
    page_number: int
    level: int
    children: List['BookmarkInfo'] = field(default_factory=list)
    
    def __repr__(self):
        return f"Bookmark('{self.title}', page={self.page_number}, level={self.level})"


@dataclass
class PageDiff:
    """Represents differences between two pages."""
    page_num_left: int
    page_num_right: int
    bookmark_left: Optional[str]
    bookmark_right: Optional[str]
    similarity_ratio: float
    changes: List[str]
    diff_lines: List[str]


@dataclass
class ComparisonResult:
    """Results of comparing two PDFs."""
    pdf1_path: str
    pdf2_path: str
    pdf1_version: str
    pdf2_version: str
    
    # Statistics
    total_pages_left: int
    total_pages_right: int
    
    # Changes detected
    modified_pages: List[PageDiff] = field(default_factory=list)
    added_pages: List[Tuple[int, str, str]] = field(default_factory=list)  # (page_num, bookmark, text_preview)
    deleted_pages: List[Tuple[int, str, str]] = field(default_factory=list)  # (page_num, bookmark, text_preview)
    
    # Bookmark changes
    added_bookmarks: List[BookmarkInfo] = field(default_factory=list)
    deleted_bookmarks: List[BookmarkInfo] = field(default_factory=list)
    modified_bookmarks: List[Tuple[BookmarkInfo, BookmarkInfo]] = field(default_factory=list)
    
    # Unchanged
    unchanged_pages: int = 0
    
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return (len(self.modified_pages) > 0 or 
                len(self.added_pages) > 0 or 
                len(self.deleted_pages) > 0)
    
    def get_summary(self) -> Dict:
        """Get a summary of the comparison."""
        return {
            'total_changes': len(self.modified_pages) + len(self.added_pages) + len(self.deleted_pages),
            'modified_pages': len(self.modified_pages),
            'added_pages': len(self.added_pages),
            'deleted_pages': len(self.deleted_pages),
            'unchanged_pages': self.unchanged_pages,
            'added_bookmarks': len(self.added_bookmarks),
            'deleted_bookmarks': len(self.deleted_bookmarks),
            'modified_bookmarks': len(self.modified_bookmarks)
        }


class PDFComparisonEngine:
    """
    Engine for comparing two PDF files and detecting changes.
    
    Uses text extraction, bookmark analysis, and similarity matching.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the comparison engine.
        
        Args:
            similarity_threshold: Minimum similarity ratio to consider pages as "similar"
                                 (0.0 to 1.0, default 0.85)
        """
        self.similarity_threshold = similarity_threshold
    
    def extract_text_from_page(self, page: fitz.Page) -> str:
        """Extract text from a PDF page."""
        try:
            text = page.get_text("text")
            return text.strip()
        except Exception as e:
            return f"[Error extracting text: {e}]"
    
    def extract_bookmarks(self, pdf_doc: fitz.Document) -> List[BookmarkInfo]:
        """Extract bookmarks (outlines) from a PDF."""
        bookmarks = []
        toc = pdf_doc.get_toc()  # Returns list of [level, title, page]
        
        for item in toc:
            level, title, page_num = item
            bookmark = BookmarkInfo(
                title=title,
                page_number=page_num,
                level=level
            )
            bookmarks.append(bookmark)
        
        return bookmarks
    
    def build_page_bookmark_map(self, pdf_doc: fitz.Document, bookmarks: List[BookmarkInfo]) -> Dict[int, str]:
        """Create a mapping of page numbers to their bookmark names."""
        page_to_bookmark = {}
        
        # Sort bookmarks by page number
        sorted_bookmarks = sorted(bookmarks, key=lambda x: x.page_number)
        
        for i, bookmark in enumerate(sorted_bookmarks):
            start_page = bookmark.page_number
            # Find the end page (start of next bookmark or end of document)
            end_page = sorted_bookmarks[i + 1].page_number if i + 1 < len(sorted_bookmarks) else len(pdf_doc)
            
            # Assign this bookmark to all pages in its range
            for page_num in range(start_page, end_page):
                if page_num not in page_to_bookmark:
                    page_to_bookmark[page_num] = bookmark.title
        
        return page_to_bookmark
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two text strings."""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def generate_diff(self, text1: str, text2: str) -> List[str]:
        """Generate a unified diff between two texts."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        diff = list(unified_diff(lines1, lines2, lineterm='', n=2))
        return diff
    
    def get_text_preview(self, text: str, max_length: int = 100) -> str:
        """Get a preview of text content."""
        text = ' '.join(text.split())  # Normalize whitespace
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def compare(self, pdf1_path: str, pdf2_path: str, 
                version1: str = "v1", version2: str = "v2") -> ComparisonResult:
        """
        Compare two PDF files and detect changes.
        
        Args:
            pdf1_path: Path to first PDF (older version)
            pdf2_path: Path to second PDF (newer version)
            version1: Version string for first PDF
            version2: Version string for second PDF
            
        Returns:
            ComparisonResult object with detailed comparison
        """
        # Open both PDFs
        pdf1 = fitz.open(pdf1_path)
        pdf2 = fitz.open(pdf2_path)
        
        # Extract bookmarks
        bookmarks1 = self.extract_bookmarks(pdf1)
        bookmarks2 = self.extract_bookmarks(pdf2)
        
        # Build page-to-bookmark mappings
        page_bookmark_map1 = self.build_page_bookmark_map(pdf1, bookmarks1)
        page_bookmark_map2 = self.build_page_bookmark_map(pdf2, bookmarks2)
        
        # Extract all pages with text
        pages1 = []
        for page_num in range(len(pdf1)):
            text = self.extract_text_from_page(pdf1[page_num])
            bookmark = page_bookmark_map1.get(page_num + 1, "No Bookmark")
            pages1.append(PageInfo(page_num + 1, text, bookmark))
        
        pages2 = []
        for page_num in range(len(pdf2)):
            text = self.extract_text_from_page(pdf2[page_num])
            bookmark = page_bookmark_map2.get(page_num + 1, "No Bookmark")
            pages2.append(PageInfo(page_num + 1, text, bookmark))
        
        # Initialize result
        result = ComparisonResult(
            pdf1_path=pdf1_path,
            pdf2_path=pdf2_path,
            pdf1_version=version1,
            pdf2_version=version2,
            total_pages_left=len(pages1),
            total_pages_right=len(pages2)
        )
        
        # Compare pages
        matched_pages2 = set()
        
        for page1 in pages1:
            best_match = None
            best_similarity = 0.0
            
            # Try to find matching page in pdf2
            for page2 in pages2:
                if page2.page_number in matched_pages2:
                    continue
                
                similarity = self.calculate_text_similarity(page1.text, page2.text)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = page2
            
            if best_match and best_similarity >= self.similarity_threshold:
                # Pages are similar
                matched_pages2.add(best_match.page_number)
                
                if best_similarity < 1.0:
                    # Modified page
                    diff_lines = self.generate_diff(page1.text, page2.text)
                    changes = self._extract_changes(diff_lines)
                    
                    page_diff = PageDiff(
                        page_num_left=page1.page_number,
                        page_num_right=best_match.page_number,
                        bookmark_left=page1.bookmark,
                        bookmark_right=best_match.bookmark,
                        similarity_ratio=best_similarity,
                        changes=changes,
                        diff_lines=diff_lines
                    )
                    result.modified_pages.append(page_diff)
                else:
                    # Unchanged
                    result.unchanged_pages += 1
            else:
                # Page deleted or heavily modified
                preview = self.get_text_preview(page1.text)
                result.deleted_pages.append((page1.page_number, page1.bookmark, preview))
        
        # Find added pages (pages in pdf2 not matched)
        for page2 in pages2:
            if page2.page_number not in matched_pages2:
                preview = self.get_text_preview(page2.text)
                result.added_pages.append((page2.page_number, page2.bookmark, preview))
        
        # Compare bookmarks
        bookmark_titles1 = {b.title for b in bookmarks1}
        bookmark_titles2 = {b.title for b in bookmarks2}
        
        added_bookmark_titles = bookmark_titles2 - bookmark_titles1
        deleted_bookmark_titles = bookmark_titles1 - bookmark_titles2
        
        result.added_bookmarks = [b for b in bookmarks2 if b.title in added_bookmark_titles]
        result.deleted_bookmarks = [b for b in bookmarks1 if b.title in deleted_bookmark_titles]
        
        # Close PDFs
        pdf1.close()
        pdf2.close()
        
        return result
    
    def _extract_changes(self, diff_lines: List[str]) -> List[str]:
        """Extract meaningful changes from diff lines."""
        changes = []
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                changes.append(f"Added: {line[1:].strip()}")
            elif line.startswith('-') and not line.startswith('---'):
                changes.append(f"Removed: {line[1:].strip()}")
        return changes[:10]  # Limit to first 10 changes
    
    def print_comparison_result(self, result: ComparisonResult, pair_number: int = 1) -> None:
        """Print detailed comparison results in a formatted way."""
        print("\n" + "=" * 100)
        print(f"🔍 COMPARISON RESULT - PAIR #{pair_number}")
        print("=" * 100)
        print(f"LEFT PDF:  {result.pdf1_version} ({result.total_pages_left} pages)")
        print(f"RIGHT PDF: {result.pdf2_version} ({result.total_pages_right} pages)")
        print(f"📄 File 1: {result.pdf1_path}")
        print(f"📄 File 2: {result.pdf2_path}")
        print()
        
        summary = result.get_summary()
        
        print("─" * 100)
        print("📊 SUMMARY:")
        print("─" * 100)
        print(f"  ✅ Unchanged Pages:     {summary['unchanged_pages']}")
        print(f"  📝 Modified Pages:      {summary['modified_pages']}")
        print(f"  ➕ Added Pages:         {summary['added_pages']}")
        print(f"  ➖ Deleted Pages:       {summary['deleted_pages']}")
        print(f"  🔖 Added Bookmarks:     {summary['added_bookmarks']}")
        print(f"  🔖 Deleted Bookmarks:   {summary['deleted_bookmarks']}")
        print(f"  📌 Total Changes:       {summary['total_changes']}")
        print()
        
        if not result.has_changes():
            print("✨ NO CHANGES DETECTED - PDFs are identical!")
            print("=" * 100)
            return
        
        # Print modified pages
        if result.modified_pages:
            print("─" * 100)
            print(f"📝 MODIFIED PAGES ({len(result.modified_pages)}):")
            print("─" * 100)
            for i, page_diff in enumerate(result.modified_pages, 1):
                print(f"\n  Change #{i}:")
                print(f"    📄 Page {page_diff.page_num_left} → Page {page_diff.page_num_right}")
                print(f"    🔖 Section: {page_diff.bookmark_left}")
                print(f"    📊 Similarity: {page_diff.similarity_ratio:.1%}")
                
                if page_diff.changes:
                    print(f"    🔍 Key Changes:")
                    for change in page_diff.changes[:5]:  # Show first 5 changes
                        print(f"       • {change}")
                print()
        
        # Print added pages
        if result.added_pages:
            print("─" * 100)
            print(f"➕ ADDED PAGES ({len(result.added_pages)}):")
            print("─" * 100)
            for page_num, bookmark, preview in result.added_pages:
                print(f"  📄 Page {page_num}")
                print(f"     🔖 Section: {bookmark}")
                print(f"     📝 Preview: {preview}")
                print()
        
        # Print deleted pages
        if result.deleted_pages:
            print("─" * 100)
            print(f"➖ DELETED PAGES ({len(result.deleted_pages)}):")
            print("─" * 100)
            for page_num, bookmark, preview in result.deleted_pages:
                print(f"  📄 Page {page_num}")
                print(f"     🔖 Section: {bookmark}")
                print(f"     📝 Preview: {preview}")
                print()
        
        # Print bookmark changes
        if result.added_bookmarks:
            print("─" * 100)
            print(f"🔖 ADDED BOOKMARKS ({len(result.added_bookmarks)}):")
            print("─" * 100)
            for bookmark in result.added_bookmarks:
                print(f"  • {bookmark.title} (page {bookmark.page_number})")
            print()
        
        if result.deleted_bookmarks:
            print("─" * 100)
            print(f"🔖 DELETED BOOKMARKS ({len(result.deleted_bookmarks)}):")
            print("─" * 100)
            for bookmark in result.deleted_bookmarks:
                print(f"  • {bookmark.title} (page {bookmark.page_number})")
            print()
        
        print("=" * 100)
        print()


def test_comparison():
    """Test function to demonstrate the comparison engine."""
    from pdf_sequencer import PDFSequencer
    
    # Create sequencer
    input_dir = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    sequencer = PDFSequencer(input_dir)
    sequencer.scan_directory()
    
    # Get comparison pairs
    pairs = sequencer.create_comparison_pairs()
    
    # Create comparison engine
    engine = PDFComparisonEngine(similarity_threshold=0.85)
    
    print("\n" + "🚀" * 50)
    print("STARTING PDF COMPARISON PIPELINE")
    print("🚀" * 50)
    
    # Compare each pair
    all_results = []
    for i, (pdf1, pdf2) in enumerate(pairs, 1):
        print(f"\n\n⏳ Processing Pair #{i}/{len(pairs)}...")
        print(f"   Comparing: {pdf1.version_string} → {pdf2.version_string}")
        
        result = engine.compare(
            pdf1_path=pdf1.filepath,
            pdf2_path=pdf2.filepath,
            version1=f"v{pdf1.version_string}",
            version2=f"v{pdf2.version_string}"
        )
        
        engine.print_comparison_result(result, pair_number=i)
        all_results.append(result)
    
    # Print final summary
    print("\n" + "🎯" * 50)
    print("FINAL SUMMARY - ALL COMPARISONS")
    print("🎯" * 50)
    
    total_changes = sum(r.get_summary()['total_changes'] for r in all_results)
    total_modified = sum(r.get_summary()['modified_pages'] for r in all_results)
    total_added = sum(r.get_summary()['added_pages'] for r in all_results)
    total_deleted = sum(r.get_summary()['deleted_pages'] for r in all_results)
    
    print(f"\n📊 Across {len(pairs)} comparisons:")
    print(f"   • Total Changes Detected: {total_changes}")
    print(f"   • Modified Pages: {total_modified}")
    print(f"   • Added Pages: {total_added}")
    print(f"   • Deleted Pages: {total_deleted}")
    print("\n✅ Comparison pipeline completed!\n")
    
    return all_results


if __name__ == "__main__":
    results = test_comparison()
