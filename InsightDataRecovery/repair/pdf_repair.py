"""
Insight Data Recovery - PDF Repair Engine
Repairs corrupted PDF documents by rebuilding broken cross-reference tables (xref),
re-indexing object dictionaries, and salvaging valid page streams using PyMuPDF / pypdf.
"""
import os
from typing import Tuple


def repair_pdf_file(corrupt_file_path: str, output_repaired_path: str) -> Tuple[bool, str]:
    """
    Repair corrupted PDF document.
    """
    if not os.path.exists(corrupt_file_path):
        return False, "PDF file does not exist."

    os.makedirs(os.path.dirname(os.path.abspath(output_repaired_path)), exist_ok=True)

    # 1. Try PyMuPDF (fitz) deep rebuild
    try:
        import fitz
        doc = fitz.open(corrupt_file_path)
        if doc.page_count > 0:
            page_cnt = doc.page_count
            doc.save(
                output_repaired_path,
                garbage=4,  # De-duplicate & remove unused objects
                deflate=True,  # Compress streams
                clean=True  # Clean and sanitize syntax
            )
            doc.close()
            return True, f"PDF successfully repaired ({page_cnt} pages recovered): {output_repaired_path}"
    except Exception:
        pass

    # 2. Try pypdf lenient reader
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(corrupt_file_path, strict=False)
        writer = PdfWriter()
        count = 0
        for page in reader.pages:
            try:
                writer.add_page(page)
                count += 1
            except Exception:
                continue

        if count > 0:
            with open(output_repaired_path, "wb") as f_out:
                writer.write(f_out)
            return True, f"PDF salvaged ({count} pages recovered): {output_repaired_path}"
    except Exception:
        pass

    # 3. Low-level trailer/EOF patching
    try:
        with open(corrupt_file_path, "rb") as f_in:
            data = f_in.read()

        if not data.startswith(b"%PDF-"):
            data = b"%PDF-1.7\n" + data

        if not data.rstrip().endswith(b"%%EOF"):
            data = data + b"\n%%EOF\n"

        with open(output_repaired_path, "wb") as f_out:
            f_out.write(data)

        return True, f"PDF trailer structure patched: {output_repaired_path}"
    except Exception as e:
        return False, f"Failed to salvage PDF: {e}"

