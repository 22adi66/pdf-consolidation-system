"""
PDF Sequencer Module
====================
This module handles intelligent sequencing and pairing of PDF files for version comparison.

It sorts PDFs by version numbers and creates comparison pairs for the consolidation pipeline.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class PDFVersion:
    """Represents a PDF file with version information."""
    filepath: str
    filename: str
    version_tuple: Tuple[int, ...]
    version_string: str
    
    def __repr__(self):
        return f"PDFVersion({self.filename}, v{self.version_string})"


class PDFSequencer:
    """
    Intelligently sequences PDF files based on version numbers.
    
    Handles various naming patterns:
    - XXyyyy-yyyy-study-design-1-0-0(english).pdf
    - XXyyyy-yyyy--study-design-2-0-4(english).pdf
    - document-v1.2.3.pdf
    - report_version_3.0.0.pdf
    """
    
    def __init__(self, input_directory: str):
        """
        Initialize the sequencer with an input directory.
        
        Args:
            input_directory: Path to directory containing PDF files
        """
        self.input_directory = Path(input_directory)
        self.pdf_files: List[PDFVersion] = []
        
    def extract_version_from_filename(self, filename: str) -> Tuple[int, ...]:
        """
        Extract version numbers from filename.
        
        Supports patterns like:
        - study-design-1-0-0 → (1, 0, 0)
        - study-design-2-0-4 → (2, 0, 4)
        - version-3.0.21 → (3, 0, 21)
        - v4.1.2 → (4, 1, 2)
        
        Args:
            filename: Name of the PDF file
            
        Returns:
            Tuple of version numbers
        """
        # Remove extension
        name_without_ext = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Pattern 1: study-design-X-Y-Z format (dashes)
        pattern1 = r'study-design-(\d+)-(\d+)-(\d+)'
        match1 = re.search(pattern1, name_without_ext)
        if match1:
            return tuple(int(x) for x in match1.groups())
        
        # Pattern 2: version-X.Y.Z or vX.Y.Z format (dots)
        pattern2 = r'(?:version[_-]?|v)(\d+)\.(\d+)\.(\d+)'
        match2 = re.search(pattern2, name_without_ext, re.IGNORECASE)
        if match2:
            return tuple(int(x) for x in match2.groups())
        
        # Pattern 3: Any sequence of numbers separated by dots or dashes
        pattern3 = r'(\d+)[.-](\d+)[.-](\d+)'
        match3 = re.search(pattern3, name_without_ext)
        if match3:
            return tuple(int(x) for x in match3.groups())
        
        # Pattern 4: Single version number
        pattern4 = r'(?:version[_-]?|v)(\d+)'
        match4 = re.search(pattern4, name_without_ext, re.IGNORECASE)
        if match4:
            return (int(match4.group(1)), 0, 0)
        
        # Fallback: No version found, use (0, 0, 0)
        return (0, 0, 0)
    
    def scan_directory(self) -> None:
        """Scan the input directory for PDF files and extract version info."""
        if not self.input_directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.input_directory}")
        
        pdf_files = list(self.input_directory.glob("*.pdf")) + \
                   list(self.input_directory.glob("*.PDF"))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in {self.input_directory}")
        
        # Use a set to track unique filenames and avoid duplicates
        seen_files = set()
        
        for pdf_path in pdf_files:
            filename = pdf_path.name
            filepath_normalized = str(pdf_path).lower()
            
            # Skip duplicates
            if filepath_normalized in seen_files:
                continue
            
            seen_files.add(filepath_normalized)
            
            version_tuple = self.extract_version_from_filename(filename)
            version_string = '.'.join(map(str, version_tuple))
            
            pdf_version = PDFVersion(
                filepath=str(pdf_path),
                filename=filename,
                version_tuple=version_tuple,
                version_string=version_string
            )
            self.pdf_files.append(pdf_version)
    
    def sort_by_version(self) -> List[PDFVersion]:
        """
        Sort PDF files by version numbers (ascending).
        
        Returns:
            List of PDFVersion objects sorted by version
        """
        return sorted(self.pdf_files, key=lambda x: x.version_tuple)
    
    def create_comparison_pairs(self) -> List[Tuple[PDFVersion, PDFVersion]]:
        """
        Create sequential pairs for comparison.
        
        For N PDFs: (pdf1, pdf2), (pdf2, pdf3), ..., (pdfN-1, pdfN)
        
        Returns:
            List of tuples representing comparison pairs
        """
        sorted_pdfs = self.sort_by_version()
        
        if len(sorted_pdfs) < 2:
            raise ValueError("Need at least 2 PDF files for comparison")
        
        pairs = []
        for i in range(len(sorted_pdfs) - 1):
            pairs.append((sorted_pdfs[i], sorted_pdfs[i + 1]))
        
        return pairs
    
    def get_base_pdf(self) -> PDFVersion:
        """
        Get the base PDF (oldest version).
        
        Returns:
            PDFVersion object representing the base PDF
        """
        sorted_pdfs = self.sort_by_version()
        return sorted_pdfs[0]
    
    def get_all_pdfs_sorted(self) -> List[PDFVersion]:
        """
        Get all PDFs sorted by version.
        
        Returns:
            List of all PDFVersion objects sorted by version
        """
        return self.sort_by_version()
    
    def print_sequence_info(self) -> None:
        """Print detailed information about PDF sequence and comparison pairs."""
        sorted_pdfs = self.sort_by_version()
        pairs = self.create_comparison_pairs()
        
        print("=" * 80)
        print("📑 PDF SEQUENCER - VERSION ANALYSIS")
        print("=" * 80)
        print(f"\n📁 Input Directory: {self.input_directory}")
        print(f"📊 Total PDF Files: {len(self.pdf_files)}\n")
        
        print("─" * 80)
        print("🔢 SORTED SEQUENCE (by version):")
        print("─" * 80)
        for i, pdf in enumerate(sorted_pdfs, 1):
            base_indicator = " [BASE]" if i == 1 else ""
            latest_indicator = " [LATEST]" if i == len(sorted_pdfs) else ""
            print(f"  {i}. Version {pdf.version_string}{base_indicator}{latest_indicator}")
            print(f"     📄 {pdf.filename}")
            print(f"     📂 {pdf.filepath}")
            print()
        
        print("─" * 80)
        print("🔗 COMPARISON PAIRS:")
        print("─" * 80)
        print(f"Total Comparisons: {len(pairs)}\n")
        
        for i, (pdf1, pdf2) in enumerate(pairs, 1):
            print(f"  Pair #{i}:")
            print(f"    LEFT  (v{pdf1.version_string}): {pdf1.filename}")
            print(f"    RIGHT (v{pdf2.version_string}): {pdf2.filename}")
            print(f"    🔍 Compare: v{pdf1.version_string} → v{pdf2.version_string}")
            print()
        
        print("─" * 80)
        print("📋 PROCESSING PIPELINE:")
        print("─" * 80)
        base_pdf = sorted_pdfs[0]
        print(f"1️⃣  Initialize with BASE: {base_pdf.filename} (v{base_pdf.version_string})")
        print(f"2️⃣  Execute {len(pairs)} sequential comparisons")
        print(f"3️⃣  Consolidate changes into single PDF with versioned bookmarks")
        print(f"4️⃣  Generate final output with all versions tracked")
        print()
        
        print("=" * 80)
        print("✅ SEQUENCE ANALYSIS COMPLETE")
        print("=" * 80)
        print()
    
    def get_sequence_summary(self) -> Dict:
        """
        Get a structured summary of the sequencing information.
        
        Returns:
            Dictionary containing sequence summary
        """
        sorted_pdfs = self.sort_by_version()
        pairs = self.create_comparison_pairs()
        
        return {
            'input_directory': str(self.input_directory),
            'total_pdfs': len(self.pdf_files),
            'base_pdf': {
                'filename': sorted_pdfs[0].filename,
                'version': sorted_pdfs[0].version_string,
                'filepath': sorted_pdfs[0].filepath
            },
            'latest_pdf': {
                'filename': sorted_pdfs[-1].filename,
                'version': sorted_pdfs[-1].version_string,
                'filepath': sorted_pdfs[-1].filepath
            },
            'sorted_sequence': [
                {
                    'index': i,
                    'filename': pdf.filename,
                    'version': pdf.version_string,
                    'filepath': pdf.filepath
                }
                for i, pdf in enumerate(sorted_pdfs, 1)
            ],
            'comparison_pairs': [
                {
                    'pair_number': i,
                    'left': {
                        'filename': pdf1.filename,
                        'version': pdf1.version_string
                    },
                    'right': {
                        'filename': pdf2.filename,
                        'version': pdf2.version_string
                    }
                }
                for i, (pdf1, pdf2) in enumerate(pairs, 1)
            ],
            'total_comparisons': len(pairs)
        }


def main():
    """Main function to demonstrate the PDF sequencer."""
    # Path to INPUT1 directory
    input_dir = r"c:\Users\Adithya_kommuri\OneDrive\Documents\GBS\INPUT1"
    
    # Create sequencer
    sequencer = PDFSequencer(input_dir)
    
    # Scan directory for PDFs
    print("🔍 Scanning directory for PDF files...")
    sequencer.scan_directory()
    print(f"✅ Found {len(sequencer.pdf_files)} PDF files\n")
    
    # Print detailed sequence information
    sequencer.print_sequence_info()
    
    # Get structured summary (useful for programmatic access)
    summary = sequencer.get_sequence_summary()
    
    return sequencer, summary


if __name__ == "__main__":
    sequencer, summary = main()
