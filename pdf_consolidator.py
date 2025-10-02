"""
PDF Consolidation Engine
=========================
This module handles the intelligent consolidation of multiple PDF versions into a single PDF
with proper version tracking and bookmark hierarchy.

Key Features:
- Initializes base PDF with Version 1 for all bookmarks
- Inserts changed pages after previous versions
- Creates versioned child bookmarks
- Handles bookmark name evolution (uses latest name)
- Fuzzy bookmark matching for slight variations
- Duplicate content detection
- Maintains correct page ordering
"""

import PyPDF2
from PyPDF2 import PdfWriter, PdfReader
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher
import os


@dataclass
class BookmarkVersion:
    """Represents a version of content under a bookmark."""
    version_number: int
    page_range: Tuple[int, int]  # Start and end page in consolidated PDF (1-indexed)
    source_pdf: str
    source_pages: List[int]  # Original page numbers from source PDF
    content_hash: str  # Hash of content for duplicate detection
    
    def __repr__(self):
        return f"Version {self.version_number} (pages {self.page_range[0]}-{self.page_range[1]})"


@dataclass
class BookmarkTracker:
    """Tracks all versions of a bookmark section."""
    current_name: str  # Latest bookmark name
    original_name: str  # Original bookmark name from base PDF
    versions: List[BookmarkVersion] = field(default_factory=list)
    name_history: List[str] = field(default_factory=list)  # Track name evolution
    
    def add_version(self, version: BookmarkVersion):
        """Add a new version to this bookmark."""
        self.versions.append(version)
    
    def update_name(self, new_name: str):
        """Update bookmark name to latest version."""
        if new_name != self.current_name:
            self.name_history.append(self.current_name)
            self.current_name = new_name
    
    def get_latest_version_number(self) -> int:
        """Get the latest version number."""
        return len(self.versions)
    
    def has_content_hash(self, content_hash: str) -> bool:
        """Check if this content already exists in any version."""
        return any(v.content_hash == content_hash for v in self.versions)
    
    def __repr__(self):
        return f"Bookmark('{self.current_name}', {len(self.versions)} versions)"


class PDFConsolidator:
    """
    Main consolidation engine that builds a single PDF from multiple versions.
    """
    
    def __init__(self, base_pdf_path: str, output_path: str = "consolidated_output.pdf"):
        """
        Initialize the consolidator.
        
        Args:
            base_pdf_path: Path to the base PDF (oldest version)
            output_path: Path for the consolidated output PDF
        """
        self.base_pdf_path = base_pdf_path
        self.output_path = output_path
        
        # Core data structures
        self.writer = PdfWriter()
        self.bookmark_trackers: Dict[str, BookmarkTracker] = {}
        self.current_page_count = 0  # Track total pages in consolidated PDF
        
        # Track which bookmarks have modifications (need version children)
        self.bookmarks_with_changes: Set[str] = set()
        
        # Content tracking for duplicate detection
        self.page_content_cache: Dict[int, str] = {}  # page_num -> content_hash
        
        # Bookmark fuzzy matching threshold
        self.bookmark_similarity_threshold = 0.8
        
        print("\n" + "🔧" * 50)
        print("PDF CONSOLIDATOR - INITIALIZATION")
        print("🔧" * 50)
        print(f"Base PDF: {base_pdf_path}")
        print(f"Output: {output_path}")
        print()
    
    def normalize_bookmark_name(self, name: str) -> str:
        """Normalize bookmark name for comparison."""
        # Remove extra whitespace, convert to lowercase, remove special chars
        normalized = name.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        return ' '.join(normalized.split())
    
    def find_matching_bookmark(self, bookmark_name: str) -> Optional[str]:
        """
        Find a matching bookmark using fuzzy matching.
        
        Returns the key of the matching bookmark tracker, or None.
        """
        normalized_target = self.normalize_bookmark_name(bookmark_name)
        
        best_match = None
        best_ratio = 0.0
        
        for tracker_key in self.bookmark_trackers.keys():
            tracker = self.bookmark_trackers[tracker_key]
            
            # Check current name
            normalized_current = self.normalize_bookmark_name(tracker.current_name)
            ratio = SequenceMatcher(None, normalized_target, normalized_current).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = tracker_key
            
            # Also check name history
            for historical_name in tracker.name_history:
                normalized_hist = self.normalize_bookmark_name(historical_name)
                ratio = SequenceMatcher(None, normalized_target, normalized_hist).ratio()
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = tracker_key
        
        if best_ratio >= self.bookmark_similarity_threshold:
            return best_match
        
        return None
    
    def calculate_content_hash(self, pdf_reader: PdfReader, page_indices: List[int]) -> str:
        """
        Calculate a hash of page content for duplicate detection.
        
        Args:
            pdf_reader: PDF reader object
            page_indices: List of page indices (0-based)
        
        Returns:
            Hash string
        """
        from comparison_engine_core import sanitize_text
        
        combined_text = ""
        for idx in page_indices:
            try:
                text = pdf_reader.pages[idx].extract_text() or ""
                combined_text += sanitize_text(text)
            except:
                combined_text += ""
        
        return str(hash(combined_text))
    
    def initialize_base_pdf(self) -> None:
        """
        Initialize the consolidated PDF with the base PDF.
        Creates Version 1 for all bookmarks.
        """
        print("📚 Step 1: Initializing with BASE PDF")
        print("─" * 80)
        
        base_reader = PdfReader(open(self.base_pdf_path, 'rb'))
        total_pages = len(base_reader.pages)
        
        print(f"   Base PDF has {total_pages} pages")
        
        # Extract bookmarks from base PDF
        from comparison_engine_core import create_page_to_bookmark_map
        bookmark_map = create_page_to_bookmark_map(base_reader)
        
        # Copy all pages from base PDF
        for page_num in range(total_pages):
            page = base_reader.pages[page_num]
            self.writer.add_page(page)
            self.current_page_count += 1
        
        print(f"   ✅ Copied {total_pages} pages to consolidated PDF")
        
        # Group pages by bookmark and create Version 1
        bookmark_pages: Dict[str, List[int]] = defaultdict(list)
        for page_num in range(1, len(bookmark_map)):
            bookmark_name = bookmark_map[page_num]
            bookmark_pages[bookmark_name].append(page_num)
        
        print(f"   📑 Found {len(bookmark_pages)} unique bookmarks")
        print()
        
        # Create bookmark trackers with Version 1
        for bookmark_name, pages in bookmark_pages.items():
            if bookmark_name == "(No Bookmark)":
                continue
            
            # Calculate content hash for these pages
            page_indices = [p - 1 for p in pages]  # Convert to 0-based
            content_hash = self.calculate_content_hash(base_reader, page_indices)
            
            # Create Version 1
            version_1 = BookmarkVersion(
                version_number=1,
                page_range=(min(pages), max(pages)),
                source_pdf=self.base_pdf_path,
                source_pages=pages,
                content_hash=content_hash
            )
            
            # Create tracker
            tracker = BookmarkTracker(
                current_name=bookmark_name,
                original_name=bookmark_name
            )
            tracker.add_version(version_1)
            
            # Use normalized name as key for consistent lookup
            tracker_key = self.normalize_bookmark_name(bookmark_name)
            self.bookmark_trackers[tracker_key] = tracker
            
            print(f"   📌 {bookmark_name}: Pages {min(pages)}-{max(pages)} ({len(pages)} pages)")
        
        print()
        print(f"✅ Base PDF initialized with {len(self.bookmark_trackers)} bookmarks")
        print(f"   ℹ️  Version children will be added only for bookmarks with modifications")
        print("─" * 80)
        print()
    
    def insert_modified_pages(self, comparison_result: Dict, source_pdf_path: str, 
                             pdf_version: str) -> None:
        """
        Insert modified pages and new bookmarks from a comparison into the consolidated PDF.
        
        Args:
            comparison_result: Result from comparison engine
            source_pdf_path: Path to the source PDF with changes
            pdf_version: Version string (e.g., "v2.0.4")
        """
        print(f"📝 Processing changes from {pdf_version}")
        print("─" * 80)
        
        if not comparison_result:
            print("   ⚠️  No comparison result provided")
            return
        
        source_reader = PdfReader(open(source_pdf_path, 'rb'))
        
        # Get comparison data
        matches = comparison_result.get('matches', [])
        unmatched2 = comparison_result.get('unmatched2', [])  # Added pages
        bookmark_map2 = comparison_result.get('bookmark_map2', [])
        bookmarks_needing_versions = comparison_result.get('bookmarks_needing_versions', {})
        
        # Group modified pages by bookmark
        modified_by_bookmark: Dict[str, List[Tuple[int, int, float]]] = defaultdict(list)
        
        for i, j, score in matches:
            if score < 1.0:  # Only non-identical pages
                page_num_right = j + 1
                bookmark_name = bookmark_map2[page_num_right] if page_num_right < len(bookmark_map2) else "(No Bookmark)"
                modified_by_bookmark[bookmark_name].append((i, j, score))
        
        # Process each bookmark with changes
        for bookmark_name, page_changes in modified_by_bookmark.items():
            if bookmark_name == "(No Bookmark)":
                continue
            
            print(f"\n   📑 Bookmark: '{bookmark_name}'")
            
            # Find matching bookmark tracker (fuzzy matching)
            tracker_key = self.find_matching_bookmark(bookmark_name)
            
            if tracker_key is None:
                print(f"      ⚠️  No matching bookmark found (creating new)")
                tracker_key = self.normalize_bookmark_name(bookmark_name)
                tracker = BookmarkTracker(
                    current_name=bookmark_name,
                    original_name=bookmark_name
                )
                self.bookmark_trackers[tracker_key] = tracker
            else:
                tracker = self.bookmark_trackers[tracker_key]
                
                # Update bookmark name to latest
                if bookmark_name != tracker.current_name:
                    print(f"      🔄 Bookmark name updated: '{tracker.current_name}' → '{bookmark_name}'")
                    tracker.update_name(bookmark_name)
            
            # Get ALL pages that belong to this bookmark from source PDF
            from comparison_engine_core import create_page_to_bookmark_map
            source_bookmark_map = create_page_to_bookmark_map(source_reader)
            
            # Find all pages for this bookmark in source PDF
            all_bookmark_pages = []
            for page_num in range(1, len(source_bookmark_map)):
                if source_bookmark_map[page_num] == bookmark_name:
                    all_bookmark_pages.append(page_num)
            
            if not all_bookmark_pages:
                print(f"      ⚠️  Could not find pages for bookmark in source PDF")
                continue
            
            # Calculate content hash for ALL pages
            all_page_indices = [p - 1 for p in all_bookmark_pages]  # Convert to 0-based
            content_hash = self.calculate_content_hash(source_reader, all_page_indices)
            
            # Check for duplicate content
            if tracker.has_content_hash(content_hash):
                print(f"      ⏭️  Skipping - content identical to existing version (duplicate)")
                continue
            
            # Insert pages RIGHT AFTER the last version of this bookmark
            last_version = tracker.versions[-1]
            insert_position = last_version.page_range[1]  # End page of last version
            start_page = insert_position + 1
            
            # Copy ALL pages of the bookmark
            pages_inserted = 0
            for page_idx in all_page_indices:
                page = source_reader.pages[page_idx]
                self.writer.insert_page(page, insert_position + pages_inserted)
                pages_inserted += 1
            
            # Update current page count for ALL trackers
            self.current_page_count += pages_inserted
            
            # Update page ranges for all subsequent versions in ALL bookmarks
            for t_key, t in self.bookmark_trackers.items():
                for v in t.versions:
                    if v.page_range[0] > insert_position:
                        v.page_range = (v.page_range[0] + pages_inserted, v.page_range[1] + pages_inserted)
            
            end_page = start_page + pages_inserted - 1
            
            # Track that this bookmark has modifications
            self.bookmarks_with_changes.add(tracker_key)
            
            # Create new version
            new_version_number = tracker.get_latest_version_number() + 1
            new_version = BookmarkVersion(
                version_number=new_version_number,
                page_range=(start_page, end_page),
                source_pdf=source_pdf_path,
                source_pages=all_bookmark_pages,  # ALL pages, not just modified
                content_hash=content_hash
            )
            
            tracker.add_version(new_version)
            
            print(f"      ✅ Version {new_version_number} added: Pages {start_page}-{end_page} ({pages_inserted} pages)")
            print(f"         All bookmark pages from source: {', '.join(map(str, all_bookmark_pages))}")
        
        # Process NEW bookmarks (from added pages that don't exist in consolidated PDF)
        if unmatched2:
            print(f"\n🆕 Processing NEW bookmarks from added pages")
            print("─" * 80)
            
            # Group added pages by bookmark
            added_by_bookmark: Dict[str, List[int]] = defaultdict(list)
            for page_idx in unmatched2:
                page_num = page_idx + 1
                bookmark_name = bookmark_map2[page_num] if page_num < len(bookmark_map2) else "(No Bookmark)"
                added_by_bookmark[bookmark_name].append(page_num)
            
            # Process each new bookmark
            for bookmark_name, added_pages in added_by_bookmark.items():
                if bookmark_name == "(No Bookmark)":
                    continue
                
                # Check if this bookmark already exists (fuzzy match)
                tracker_key = self.find_matching_bookmark(bookmark_name)
                
                if tracker_key is not None:
                    # Bookmark exists, skip (already handled in modified section)
                    continue
                
                print(f"\n   🆕 NEW Bookmark: '{bookmark_name}'")
                
                # Get ALL pages for this NEW bookmark from source PDF
                from comparison_engine_core import create_page_to_bookmark_map
                source_bookmark_map = create_page_to_bookmark_map(source_reader)
                
                all_bookmark_pages = []
                for page_num in range(1, len(source_bookmark_map)):
                    if source_bookmark_map[page_num] == bookmark_name:
                        all_bookmark_pages.append(page_num)
                
                if not all_bookmark_pages:
                    print(f"      ⚠️  Could not find pages for new bookmark in source PDF")
                    continue
                
                # Calculate content hash
                all_page_indices = [p - 1 for p in all_bookmark_pages]
                content_hash = self.calculate_content_hash(source_reader, all_page_indices)
                
                # Insert pages at the END of consolidated PDF
                insert_position = self.current_page_count
                start_page = insert_position + 1
                
                # Copy ALL pages of the new bookmark
                pages_inserted = 0
                for page_idx in all_page_indices:
                    page = source_reader.pages[page_idx]
                    self.writer.add_page(page)
                    pages_inserted += 1
                
                self.current_page_count += pages_inserted
                end_page = self.current_page_count
                
                # Create NEW bookmark tracker with Version 1
                tracker_key = self.normalize_bookmark_name(bookmark_name)
                tracker = BookmarkTracker(
                    current_name=bookmark_name,
                    original_name=bookmark_name
                )
                
                # Add Version 1 for this new bookmark
                version_1 = BookmarkVersion(
                    version_number=1,
                    page_range=(start_page, end_page),
                    source_pdf=source_pdf_path,
                    source_pages=all_bookmark_pages,
                    content_hash=content_hash
                )
                
                tracker.add_version(version_1)
                self.bookmark_trackers[tracker_key] = tracker
                
                # Mark as having changes (so it gets version children in hierarchy)
                self.bookmarks_with_changes.add(tracker_key)
                
                print(f"      ✅ NEW bookmark added with Version 1: Pages {start_page}-{end_page} ({pages_inserted} pages)")
                print(f"         Source pages: {', '.join(map(str, all_bookmark_pages))}")
                print(f"         From PDF: {pdf_version}")
        
        print()
        print(f"✅ Processed changes from {pdf_version}")
        print("─" * 80)
        print()
    
    def build_bookmark_hierarchy(self) -> None:
        """
        Build the hierarchical bookmark structure in the consolidated PDF.
        
        Structure:
        Bookmark Name (Latest)
          ├─ Version 1
          ├─ Version 2
          └─ Version 3
        """
        print("🔖 Building Bookmark Hierarchy")
        print("─" * 80)
        
        # Sort bookmarks for consistent ordering
        sorted_trackers = sorted(self.bookmark_trackers.items(), 
                                key=lambda x: x[1].versions[0].page_range[0])
        
        for tracker_key, tracker in sorted_trackers:
            # Add parent bookmark (uses latest name)
            parent_page = tracker.versions[0].page_range[0] - 1  # 0-indexed
            
            # Check if this bookmark has modifications
            has_changes = tracker_key in self.bookmarks_with_changes
            
            if has_changes:
                # Bookmark WITH changes: Create parent with version children
                parent_bookmark = self.writer.add_outline_item(
                    title=tracker.current_name,
                    page_number=parent_page,
                    parent=None
                )
                
                print(f"   📌 {tracker.current_name}")
                
                # Add child bookmarks for each version
                for version in tracker.versions:
                    version_title = f"Version {version.version_number}"
                    version_page = version.page_range[0] - 1  # 0-indexed
                    
                    self.writer.add_outline_item(
                        title=version_title,
                        page_number=version_page,
                        parent=parent_bookmark
                    )
                    
                    print(f"      ├─ {version_title}: Pages {version.page_range[0]}-{version.page_range[1]}")
            else:
                # Bookmark WITHOUT changes: Simple bookmark, no version children
                self.writer.add_outline_item(
                    title=tracker.current_name,
                    page_number=parent_page,
                    parent=None
                )
                
                version = tracker.versions[0]
                print(f"   📌 {tracker.current_name}: Pages {version.page_range[0]}-{version.page_range[1]}")
        
        print()
        print(f"✅ Bookmark hierarchy built with {len(self.bookmark_trackers)} sections")
        print("─" * 80)
        print()
    
    def save(self) -> None:
        """Save the consolidated PDF to disk."""
        print("💾 Saving Consolidated PDF")
        print("─" * 80)
        
        with open(self.output_path, 'wb') as output_file:
            self.writer.write(output_file)
        
        file_size = os.path.getsize(self.output_path) / (1024 * 1024)  # MB
        
        print(f"   ✅ Saved: {self.output_path}")
        print(f"   📊 Total Pages: {self.current_page_count}")
        print(f"   💾 File Size: {file_size:.2f} MB")
        print("─" * 80)
        print()
    
    def print_summary(self) -> None:
        """Print a detailed summary of the consolidation."""
        print("\n" + "📊" * 50)
        print("CONSOLIDATION SUMMARY")
        print("📊" * 50)
        print()
        
        print(f"📄 Output PDF: {self.output_path}")
        print(f"📄 Total Pages: {self.current_page_count}")
        print(f"📑 Total Bookmarks: {len(self.bookmark_trackers)}")
        print()
        
        bookmarks_with_versions = len(self.bookmarks_with_changes)
        bookmarks_without_changes = len(self.bookmark_trackers) - bookmarks_with_versions
        
        total_versions = sum(len(t.versions) for k, t in self.bookmark_trackers.items() if k in self.bookmarks_with_changes)
        
        print(f"📈 Statistics:")
        print(f"   Bookmarks WITH changes (have version children): {bookmarks_with_versions}")
        print(f"   Bookmarks WITHOUT changes (simple bookmarks): {bookmarks_without_changes}")
        print(f"   Total Version Children Created: {total_versions}")
        print()
        
        # Show bookmarks with most versions
        most_versions = sorted(self.bookmark_trackers.values(), 
                              key=lambda t: len(t.versions), reverse=True)[:5]
        
        if most_versions:
            print("🏆 Top Bookmarks by Version Count:")
            for tracker in most_versions:
                if len(tracker.versions) > 1:
                    print(f"   {len(tracker.versions)} versions: {tracker.current_name}")
        
        print()
        print("✅ CONSOLIDATION COMPLETE!")
        print("📊" * 50)
        print()


def test_consolidator():
    """Test the consolidator with sample data."""
    base_pdf = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1\XXyyyy-yyyy-study-design-1-0-0(english).pdf"
    output_pdf = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\consolidated_test.pdf"
    
    consolidator = PDFConsolidator(base_pdf, output_pdf)
    consolidator.initialize_base_pdf()
    consolidator.build_bookmark_hierarchy()
    consolidator.save()
    consolidator.print_summary()
    
    return consolidator


if __name__ == "__main__":
    consolidator = test_consolidator()
