"""
Insight Data Recovery - Office Document Repair Suite
Repairs corrupted Word (.docx), Excel (.xlsx), and PowerPoint (.pptx) documents
by rebuilding damaged ZIP containers, fixing truncated XML trees, and salvaging intact contents.
"""
import os
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Tuple, List, Optional


def repair_truncated_xml(raw_xml: bytes) -> bytes:
    """
    Repair truncated or malformed XML by sanitizing control characters,
    stripping incomplete closing tags, and closing open tags cleanly.
    """
    try:
        # Decode with permissive error handling
        text = raw_xml.decode("utf-8", errors="ignore")
        # Remove invalid XML control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)

        # Find all open tags
        open_tags = []
        tag_pattern = re.compile(r"<(/)?([a-zA-Z0-9_:\-]+)([^>]*)>")
        for match in tag_pattern.finditer(text):
            is_closing, tag_name, attrs = match.groups()
            is_self_closing = attrs.strip().endswith("/")
            if is_self_closing or tag_name.startswith("?") or tag_name.startswith("!"):
                continue
            if is_closing:
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
            else:
                open_tags.append(tag_name)

        # Append missing closing tags in reverse order
        for tag in reversed(open_tags):
            text += f"</{tag}>"

        # Validate with ElementTree
        try:
            ET.fromstring(text.encode("utf-8"))
            return text.encode("utf-8")
        except Exception:
            return raw_xml
    except Exception:
        return raw_xml


def repair_office_file(corrupt_file_path: str, output_repaired_path: str) -> Tuple[bool, str]:
    """
    Repair damaged .docx, .xlsx, or .pptx file.
    """
    if not os.path.exists(corrupt_file_path):
        return False, "File does not exist."

    ext = os.path.splitext(corrupt_file_path)[1].lower()
    salvaged_entries = {}

    # 1. Try standard zipfile first
    try:
        with zipfile.ZipFile(corrupt_file_path, "r") as z_in:
            for name in z_in.namelist():
                try:
                    salvaged_entries[name] = z_in.read(name)
                except Exception:
                    pass
    except Exception:
        # 2. Carve raw PK\x03\x04 streams manually if ZIP index is broken
        try:
            with open(corrupt_file_path, "rb") as f:
                data = f.read()

            pos = 0
            while True:
                idx = data.find(b"PK\x03\x04", pos)
                if idx == -1:
                    break

                # Parse local file header:
                # Offset 18: Compressed size (4 bytes), Offset 22: Uncompressed size (4 bytes)
                # Offset 26: Filename length (2 bytes), Offset 28: Extra field length (2 bytes)
                if idx + 30 <= len(data):
                    fn_len = int.from_bytes(data[idx + 26:idx + 28], "little")
                    extra_len = int.from_bytes(data[idx + 28:idx + 30], "little")
                    name_start = idx + 30
                    name_end = name_start + fn_len
                    if name_end <= len(data):
                        entry_name = data[name_start:name_end].decode("utf-8", errors="ignore")
                        data_start = name_end + extra_len
                        # Next PK or reasonable chunk
                        next_pk = data.find(b"PK", data_start)
                        entry_data = data[data_start:next_pk] if next_pk != -1 else data[data_start:data_start + 1000000]
                        if entry_name:
                            salvaged_entries[entry_name] = entry_data
                pos = idx + 4
        except Exception:
            pass

    if not salvaged_entries:
        # Fallback: Extract pure text strings from binary stream
        try:
            with open(corrupt_file_path, "rb") as f:
                raw_bytes = f.read()
            # Extract printable ASCII/UTF-8 and Arabic Unicode ranges
            extracted_text = re.findall(r"[\u0600-\u06FF\w\s.,!?:;\-\(\)]{4,}", raw_bytes.decode("utf-8", errors="ignore"))
            clean_content = "\n".join(extracted_text)

            txt_out = os.path.splitext(output_repaired_path)[0] + "_salvaged_text.txt"
            with open(txt_out, "w", encoding="utf-8") as f_txt:
                f_txt.write("=== Insight Data Recovery: Salvaged Document Text ===\n\n")
                f_txt.write(clean_content)
            return True, f"Repaired into salvaged text document: {txt_out}"
        except Exception as e:
            return False, f"Failed to salvage office file: {e}"

    # Rebuild XML entries
    for name, content in list(salvaged_entries.items()):
        if name.endswith(".xml") or name.endswith(".rels"):
            salvaged_entries[name] = repair_truncated_xml(content)

    # Ensure required package structures exist
    if "[Content_Types].xml" not in salvaged_entries:
        if ext == ".docx":
            salvaged_entries["[Content_Types].xml"] = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
        elif ext == ".xlsx":
            salvaged_entries["[Content_Types].xml"] = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>'

    # Assemble fresh, valid ZIP archive
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_repaired_path)), exist_ok=True)
        with zipfile.ZipFile(output_repaired_path, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
            for name, content in salvaged_entries.items():
                z_out.writestr(name, content)
        return True, f"Document repaired successfully: {output_repaired_path}"
    except Exception as e:
        return False, f"Failed to compile repaired document: {e}"

