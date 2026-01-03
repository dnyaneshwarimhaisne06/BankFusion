# backend/pdf_extractor/__init__.py
from .base_extractor import BasePDFExtractor
from .hdfc_extractor import HDFCExtractor
from .axis_extractor import AxisExtractor
from .sbi_extractor import SBIExtractor
from .union_extractor import UnionExtractor
from .boi_extractor import BOIExtractor
from .central_extractor import CentralExtractor

# Import functions from the pdf_extractor.py file in the parent directory
import sys
import os
# Get the parent directory (backend/)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from the pdf_extractor.py file (not the package)
import importlib.util
pdf_extractor_file_path = os.path.join(parent_dir, 'pdf_extractor.py')
spec = importlib.util.spec_from_file_location("pdf_extractor_module", pdf_extractor_file_path)
pdf_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_extractor_module)

# Re-export the functions
extract_account_info = pdf_extractor_module.extract_account_info
extract_transactions = pdf_extractor_module.extract_transactions

__all__ = [
    'BasePDFExtractor',
    'HDFCExtractor',
    'AxisExtractor',
    'SBIExtractor',
    'UnionExtractor',
    'BOIExtractor',
    'CentralExtractor',
    'extract_account_info',
    'extract_transactions'
]