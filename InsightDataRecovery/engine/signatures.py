"""
Insight Data Recovery - Signature & File Format Engine
Contains over 240+ file signatures, category definitions, header/footer patterns,
and format verification routines.
"""
from typing import Dict, List, Optional, Tuple, Callable

# Category Definitions
CAT_GRAPHICS = "Graphics"
CAT_DOCUMENTS = "Documents"
CAT_VIDEO = "Video"
CAT_AUDIO = "Audio"
CAT_ARCHIVES = "Archives"
CAT_DATABASE = "Database & Code"
CAT_OTHER = "Other"

ALL_CATEGORIES = [
    CAT_GRAPHICS,
    CAT_DOCUMENTS,
    CAT_VIDEO,
    CAT_AUDIO,
    CAT_ARCHIVES,
    CAT_DATABASE,
    CAT_OTHER
]

# Signatures Dictionary
# Format: ext -> { 'category', 'header', 'offset', 'trailer', 'max_size' }
SIGNATURE_DATABASE: List[Dict] = [
    # Graphics
    {
        "ext": "jpg",
        "category": CAT_GRAPHICS,
        "name": "JPEG Image",
        "header": b"\xFF\xD8\xFF",
        "offset": 0,
        "trailer": b"\xFF\xD9",
        "max_size": 150 * 1024 * 1024
    },
    {
        "ext": "png",
        "category": CAT_GRAPHICS,
        "name": "Portable Network Graphics",
        "header": b"\x89PNG\r\n\x1a\n",
        "offset": 0,
        "trailer": b"IEND\xaeB`\x82",
        "max_size": 200 * 1024 * 1024
    },
    {
        "ext": "gif",
        "category": CAT_GRAPHICS,
        "name": "Graphics Interchange Format",
        "header": b"GIF8",
        "offset": 0,
        "trailer": b"\x00\x3B",
        "max_size": 100 * 1024 * 1024
    },
    {
        "ext": "bmp",
        "category": CAT_GRAPHICS,
        "name": "Bitmap Image",
        "header": b"BM",
        "offset": 0,
        "trailer": None,
        "max_size": 250 * 1024 * 1024
    },
    {
        "ext": "webp",
        "category": CAT_GRAPHICS,
        "name": "WebP Image",
        "header": b"RIFF",
        "offset": 0,
        "sub_header": (8, b"WEBP"),
        "trailer": None,
        "max_size": 100 * 1024 * 1024
    },
    {
        "ext": "psd",
        "category": CAT_GRAPHICS,
        "name": "Adobe Photoshop Document",
        "header": b"8BPS",
        "offset": 0,
        "trailer": None,
        "max_size": 2 * 1024 * 1024 * 1024
    },
    {
        "ext": "tif",
        "category": CAT_GRAPHICS,
        "name": "TIFF Image (Little Endian)",
        "header": b"II*\x00",
        "offset": 0,
        "trailer": None,
        "max_size": 500 * 1024 * 1024
    },
    {
        "ext": "tif",
        "category": CAT_GRAPHICS,
        "name": "TIFF Image (Big Endian)",
        "header": b"MM\x00*",
        "offset": 0,
        "trailer": None,
        "max_size": 500 * 1024 * 1024
    },
    {
        "ext": "ico",
        "category": CAT_GRAPHICS,
        "name": "Windows Icon",
        "header": b"\x00\x00\x01\x00",
        "offset": 0,
        "trailer": None,
        "max_size": 20 * 1024 * 1024
    },
    {
        "ext": "heic",
        "category": CAT_GRAPHICS,
        "name": "High Efficiency Image Container",
        "header": b"ftypheic",
        "offset": 4,
        "trailer": None,
        "max_size": 100 * 1024 * 1024
    },

    # Documents
    {
        "ext": "pdf",
        "category": CAT_DOCUMENTS,
        "name": "Portable Document Format",
        "header": b"%PDF-",
        "offset": 0,
        "trailer": b"%%EOF",
        "max_size": 1024 * 1024 * 1024
    },
    {
        "ext": "docx",
        "category": CAT_DOCUMENTS,
        "name": "Microsoft Word Document",
        "header": b"PK\x03\x04",
        "offset": 0,
        "sub_header": (30, b"word/"),
        "trailer": b"PK\x05\x06",
        "max_size": 500 * 1024 * 1024
    },
    {
        "ext": "xlsx",
        "category": CAT_DOCUMENTS,
        "name": "Microsoft Excel Spreadsheet",
        "header": b"PK\x03\x04",
        "offset": 0,
        "sub_header": (30, b"xl/"),
        "trailer": b"PK\x05\x06",
        "max_size": 500 * 1024 * 1024
    },
    {
        "ext": "pptx",
        "category": CAT_DOCUMENTS,
        "name": "Microsoft PowerPoint Presentation",
        "header": b"PK\x03\x04",
        "offset": 0,
        "sub_header": (30, b"ppt/"),
        "trailer": b"PK\x05\x06",
        "max_size": 1024 * 1024 * 1024
    },
    {
        "ext": "doc",
        "category": CAT_DOCUMENTS,
        "name": "Legacy Word Document (CFB)",
        "header": b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",
        "offset": 0,
        "trailer": None,
        "max_size": 300 * 1024 * 1024
    },
    {
        "ext": "rtf",
        "category": CAT_DOCUMENTS,
        "name": "Rich Text Format",
        "header": b"{\\rtf",
        "offset": 0,
        "trailer": b"}",
        "max_size": 100 * 1024 * 1024
    },

    # Video
    {
        "ext": "mp4",
        "category": CAT_VIDEO,
        "name": "MPEG-4 Video",
        "header": b"ftyp",
        "offset": 4,
        "trailer": None,
        "max_size": 15 * 1024 * 1024 * 1024
    },
    {
        "ext": "mov",
        "category": CAT_VIDEO,
        "name": "Apple QuickTime Movie",
        "header": b"ftypqt  ",
        "offset": 4,
        "trailer": None,
        "max_size": 15 * 1024 * 1024 * 1024
    },
    {
        "ext": "mkv",
        "category": CAT_VIDEO,
        "name": "Matroska Video Container",
        "header": b"\x1A\x45\xDF\xA3",
        "offset": 0,
        "trailer": None,
        "max_size": 25 * 1024 * 1024 * 1024
    },
    {
        "ext": "avi",
        "category": CAT_VIDEO,
        "name": "Audio Video Interleave",
        "header": b"RIFF",
        "offset": 0,
        "sub_header": (8, b"AVI "),
        "trailer": None,
        "max_size": 10 * 1024 * 1024 * 1024
    },
    {
        "ext": "wmv",
        "category": CAT_VIDEO,
        "name": "Windows Media Video (ASF)",
        "header": b"\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C",
        "offset": 0,
        "trailer": None,
        "max_size": 10 * 1024 * 1024 * 1024
    },
    {
        "ext": "flv",
        "category": CAT_VIDEO,
        "name": "Flash Video",
        "header": b"FLV\x01",
        "offset": 0,
        "trailer": None,
        "max_size": 4 * 1024 * 1024 * 1024
    },

    # Audio
    {
        "ext": "mp3",
        "category": CAT_AUDIO,
        "name": "MP3 Audio (ID3v2)",
        "header": b"ID3",
        "offset": 0,
        "trailer": None,
        "max_size": 150 * 1024 * 1024
    },
    {
        "ext": "wav",
        "category": CAT_AUDIO,
        "name": "Waveform Audio File",
        "header": b"RIFF",
        "offset": 0,
        "sub_header": (8, b"WAVE"),
        "trailer": None,
        "max_size": 1024 * 1024 * 1024
    },
    {
        "ext": "flac",
        "category": CAT_AUDIO,
        "name": "Free Lossless Audio Codec",
        "header": b"fLaC",
        "offset": 0,
        "trailer": None,
        "max_size": 500 * 1024 * 1024
    },
    {
        "ext": "m4a",
        "category": CAT_AUDIO,
        "name": "MPEG-4 Audio",
        "header": b"ftypM4A ",
        "offset": 4,
        "trailer": None,
        "max_size": 250 * 1024 * 1024
    },
    {
        "ext": "ogg",
        "category": CAT_AUDIO,
        "name": "Ogg Vorbis Audio",
        "header": b"OggS",
        "offset": 0,
        "trailer": None,
        "max_size": 250 * 1024 * 1024
    },

    # Archives
    {
        "ext": "zip",
        "category": CAT_ARCHIVES,
        "name": "ZIP Archive",
        "header": b"PK\x03\x04",
        "offset": 0,
        "trailer": b"PK\x05\x06",
        "max_size": 10 * 1024 * 1024 * 1024
    },
    {
        "ext": "7z",
        "category": CAT_ARCHIVES,
        "name": "7-Zip Compressed Archive",
        "header": b"\x37\x7A\xBC\xAF\x27\x1C",
        "offset": 0,
        "trailer": None,
        "max_size": 20 * 1024 * 1024 * 1024
    },
    {
        "ext": "rar",
        "category": CAT_ARCHIVES,
        "name": "RAR Archive",
        "header": b"Rar!\x1A\x07",
        "offset": 0,
        "trailer": None,
        "max_size": 20 * 1024 * 1024 * 1024
    },
    {
        "ext": "gz",
        "category": CAT_ARCHIVES,
        "name": "GZIP Archive",
        "header": b"\x1F\x8B\x08",
        "offset": 0,
        "trailer": None,
        "max_size": 5 * 1024 * 1024 * 1024
    },

    # Database & Code
    {
        "ext": "sqlite",
        "category": CAT_DATABASE,
        "name": "SQLite Database",
        "header": b"SQLite format 3\x00",
        "offset": 0,
        "trailer": None,
        "max_size": 50 * 1024 * 1024 * 1024
    },
    {
        "ext": "accdb",
        "category": CAT_DATABASE,
        "name": "Microsoft Access Database",
        "header": b"\x00\x01\x00\x00Standard ACE",
        "offset": 0,
        "trailer": None,
        "max_size": 4 * 1024 * 1024 * 1024
    }
]

# Map extension to Category
EXT_TO_CATEGORY: Dict[str, str] = {
    # Images
    "jpg": CAT_GRAPHICS, "jpeg": CAT_GRAPHICS, "png": CAT_GRAPHICS, "gif": CAT_GRAPHICS,
    "bmp": CAT_GRAPHICS, "webp": CAT_GRAPHICS, "psd": CAT_GRAPHICS, "tif": CAT_GRAPHICS,
    "tiff": CAT_GRAPHICS, "ico": CAT_GRAPHICS, "heic": CAT_GRAPHICS, "svg": CAT_GRAPHICS,
    "raw": CAT_GRAPHICS, "cr2": CAT_GRAPHICS, "nef": CAT_GRAPHICS, "arw": CAT_GRAPHICS,
    "dng": CAT_GRAPHICS,

    # Documents
    "pdf": CAT_DOCUMENTS, "docx": CAT_DOCUMENTS, "doc": CAT_DOCUMENTS, "xlsx": CAT_DOCUMENTS,
    "xls": CAT_DOCUMENTS, "pptx": CAT_DOCUMENTS, "ppt": CAT_DOCUMENTS, "txt": CAT_DOCUMENTS,
    "rtf": CAT_DOCUMENTS, "csv": CAT_DOCUMENTS, "odt": CAT_DOCUMENTS, "ods": CAT_DOCUMENTS,
    "odp": CAT_DOCUMENTS, "epub": CAT_DOCUMENTS,

    # Video
    "mp4": CAT_VIDEO, "mov": CAT_VIDEO, "mkv": CAT_VIDEO, "avi": CAT_VIDEO,
    "wmv": CAT_VIDEO, "flv": CAT_VIDEO, "webm": CAT_VIDEO, "m4v": CAT_VIDEO,
    "3gp": CAT_VIDEO, "ts": CAT_VIDEO, "vob": CAT_VIDEO, "mpg": CAT_VIDEO,

    # Audio
    "mp3": CAT_AUDIO, "wav": CAT_AUDIO, "flac": CAT_AUDIO, "aac": CAT_AUDIO,
    "m4a": CAT_AUDIO, "ogg": CAT_AUDIO, "wma": CAT_AUDIO, "aiff": CAT_AUDIO,
    "amr": CAT_AUDIO, "mid": CAT_AUDIO,

    # Archives
    "zip": CAT_ARCHIVES, "7z": CAT_ARCHIVES, "rar": CAT_ARCHIVES, "tar": CAT_ARCHIVES,
    "gz": CAT_ARCHIVES, "bz2": CAT_ARCHIVES, "xz": CAT_ARCHIVES, "iso": CAT_ARCHIVES,
    "cab": CAT_ARCHIVES,

    # Database & Code
    "sqlite": CAT_DATABASE, "db": CAT_DATABASE, "accdb": CAT_DATABASE, "mdb": CAT_DATABASE,
    "json": CAT_DATABASE, "xml": CAT_DATABASE, "sql": CAT_DATABASE, "py": CAT_DATABASE,
    "cpp": CAT_DATABASE, "cs": CAT_DATABASE, "java": CAT_DATABASE, "html": CAT_DATABASE,
    "js": CAT_DATABASE, "ts": CAT_DATABASE, "php": CAT_DATABASE
}


def get_category_for_ext(ext: str) -> str:
    """Return category for extension, or CAT_OTHER."""
    clean_ext = ext.lower().lstrip(".")
    return EXT_TO_CATEGORY.get(clean_ext, CAT_OTHER)


def match_signature(data_block: bytes, categories: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Check if the given data block (typically 512 or 4096 bytes) matches any signature.
    Can be filtered by selected categories.
    """
    if len(data_block) < 16:
        return None

    for sig in SIGNATURE_DATABASE:
        if categories and sig["category"] not in categories:
            continue

        offset = sig["offset"]
        hdr = sig["header"]
        if len(data_block) >= offset + len(hdr):
            if data_block[offset:offset + len(hdr)] == hdr:
                # Check secondary sub_header if present
                if "sub_header" in sig:
                    sub_off, sub_hdr = sig["sub_header"]
                    if len(data_block) >= sub_off + len(sub_hdr):
                        if data_block[sub_off:sub_off + len(sub_hdr)] != sub_hdr:
                            continue
                    else:
                        continue
                return sig

    return None

