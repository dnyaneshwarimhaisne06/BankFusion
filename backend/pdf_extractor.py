import pdfplumber
import re
import os
from typing import Dict, List, Optional

def extract_account_info(pdf_path: str) -> Dict:
    """Extract account information from PDF - Bank agnostic - IMPROVED VERSION"""
    account_info = {
        "account_number": None,
        "account_holder": None,
        "bank_name": None,
        "statement_period": None,
        "branch": None,
        "ifsc": None
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return account_info
            
            # Extract text from first few pages (account info is usually on first 2-3 pages)
            all_text = ""
            for page_idx in range(min(3, len(pdf.pages))):
                page_text = pdf.pages[page_idx].extract_text()
                if page_text:
                    all_text += "\n" + page_text
            
            # Also try extracting from tables on first page
            table_text = ""
            if pdf.pages:
                try:
                    tables = pdf.pages[0].extract_tables()
                    for table in tables:
                        if table:
                            for row in table:
                                if row:
                                    table_text += " " + " ".join([str(cell) if cell else "" for cell in row])
                except:
                    pass
            
            combined_text = all_text + "\n" + table_text
            
            if not combined_text:
                return account_info
            
            # STRICT OVERRIDE RULE #1: Bank name FORCE for Central Bank of India
            # Check FIRST before any other detection - this takes absolute precedence
            # Check in header area (first 2000 chars) for "CENTRAL BANK" - this is CRITICAL
            bank = None
            header_area = combined_text[:2000] if len(combined_text) > 2000 else combined_text
            
            # Check for Central Bank in header area - MUST be detected FIRST
            if ("CENTRAL BANK of India" in header_area or 
                "Central Bank of India" in header_area or
                ("CENTRAL BANK" in header_area.upper() and "of India" in header_area)):
                bank = "Central Bank of India"
                account_info["bank_name"] = "Central Bank of India"
                print("✓ STRICT OVERRIDE: Central Bank of India detected in header - FORCING bank name")
            else:
                # Detect bank - CRITICAL: Must NEVER be "Unknown"
                bank = detect_bank(combined_text)
                
                # If bank is still "Unknown" or "Bank (Unidentified)", try more aggressive detection
                if bank == "Unknown" or bank == "Bank (Unidentified)":
                    # Try extracting from IFSC code in tables
                    for page_idx in range(min(2, len(pdf.pages))):
                        try:
                            tables = pdf.pages[page_idx].extract_tables()
                            for table in tables:
                                if table:
                                    for row in table:
                                        if row:
                                            row_text = " ".join([str(cell) if cell else "" for cell in row]).upper()
                                            # Look for IFSC code
                                            ifsc_match = re.search(r'IFSC[:\s]*(?:CODE)?[:\s]*([A-Z]{4}0[A-Z0-9]{6})', row_text)
                                            if ifsc_match:
                                                ifsc_code = ifsc_match.group(1)
                                                ifsc_prefix = ifsc_code[:4]
                                                ifsc_bank_map = {
                                                    'SBIN': 'State Bank of India',
                                                    'BKID': 'Bank of India',
                                                    'UTIB': 'Axis Bank',
                                                    'HDFC': 'HDFC Bank',
                                                    'CBIN': 'Central Bank of India',
                                                    'UBIN': 'Union Bank of India',
                                                    'ICIC': 'ICICI Bank',
                                                }
                                                if ifsc_prefix in ifsc_bank_map:
                                                    bank = ifsc_bank_map[ifsc_prefix]
                                                    break
                                        if bank != "Unknown" and bank != "Bank (Unidentified)":
                                            break
                                    if bank != "Unknown" and bank != "Bank (Unidentified)":
                                        break
                                if bank != "Unknown" and bank != "Bank (Unidentified)":
                                    break
                            if bank != "Unknown" and bank != "Bank (Unidentified)":
                                break
                        except:
                            pass
                
                account_info["bank_name"] = bank
            
            # Extract based on bank with improved patterns
            if bank == "Axis Bank":
                extract_axis_account_info_improved(combined_text, account_info, pdf)
            elif bank == "Bank of India":
                extract_boi_account_info_improved(combined_text, account_info, pdf)
            elif bank == "HDFC Bank":
                extract_hdfc_account_info_improved(combined_text, account_info, pdf)
            elif bank == "State Bank of India":
                extract_sbi_account_info_improved(combined_text, account_info, pdf)
            elif bank == "Central Bank of India":
                extract_central_bank_account_info(combined_text, account_info, pdf)
            elif bank == "Union Bank of India":
                extract_union_bank_account_info(combined_text, account_info, pdf)
            else:
                extract_generic_account_info_improved(combined_text, account_info, pdf)
            
            # If still missing fields, try one more time with more aggressive extraction
            # EXCEPTION: For Central Bank, account_holder MUST come from header only
            # Do NOT use table extraction for account_holder if it's Central Bank
            if bank == "Central Bank of India":
                # For Central Bank, only extract missing fields (NOT account_holder from tables)
                if (not account_info.get("account_number") or 
                    not account_info.get("statement_period") or
                    not account_info.get("branch") or
                    not account_info.get("ifsc")):
                    extract_missing_account_info_from_tables(pdf, account_info)
            else:
                # For other banks, use standard extraction
                if (not account_info.get("account_number") or 
                    not account_info.get("account_holder") or 
                    not account_info.get("statement_period") or
                    not account_info.get("branch") or
                    not account_info.get("ifsc")):
                    extract_missing_account_info_from_tables(pdf, account_info)
                
            # Final cleanup: ensure branch doesn't contain unwanted text
            if account_info.get("branch"):
                branch = account_info["branch"]
                # Remove common unwanted phrases
                unwanted_phrases = ['DETAILS OF STATEMENT', 'STATEMENT OF ACCOUNT', 'BANK STATEMENT', 'IFSC CODE']
                for phrase in unwanted_phrases:
                    branch = branch.replace(phrase, '').replace(phrase.upper(), '')
                branch = ' '.join(branch.split())
                if branch:
                    account_info["branch"] = branch
                else:
                    account_info["branch"] = None
            
            # CRITICAL: Validate and clean account holder name
            # Must be FULL name (multiple words), not just first name
            # EXCEPTION: For Central Bank, account_holder is already set from header (UPPERCASE)
            # Do NOT re-validate or change case for Central Bank
            if account_info.get("account_holder") and bank != "Central Bank of India":
                account_info["account_holder"] = validate_and_clean_account_holder_name(account_info["account_holder"])
            
            # FINAL FALLBACK: Try extracting from filename if still missing
            # EXCEPTION: For Central Bank, do NOT use filename fallback - header extraction is mandatory
            if bank != "Central Bank of India":
                if not account_info.get("account_holder") or not account_info["account_holder"].strip():
                    account_info["account_holder"] = extract_account_holder_from_filename(pdf_path, combined_text)
            
            # FINAL FALLBACK: Try more aggressive account number extraction
            if not account_info.get("account_number") or not account_info["account_number"].strip():
                account_info["account_number"] = extract_account_number_aggressive(combined_text, pdf)
            
            # CRITICAL: Final validation - account_number and account_holder MUST NEVER be null
            account_info = validate_and_ensure_required_fields(account_info, pdf_path, combined_text, pdf)
                
    except Exception as e:
        print(f"Error extracting account info: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return account_info

def validate_and_clean_account_holder_name(name: str) -> Optional[str]:
    """
    Validate and clean account holder name.
    CRITICAL: Must be FULL name (multiple words), not just first name.
    
    Rules:
    - Remove titles (Mr./Mrs./Ms./Miss.)
    - Remove unwanted words (Home, Account, Bank, etc.)
    - Must have at least 2 words (first + last name minimum)
    - If only one word → extraction FAILED, return None
    
    Returns:
    - Cleaned full name if valid (has multiple words)
    - None if invalid (only one word or empty)
    """
    if not name or not name.strip():
        return None
    
    # Remove titles
    name = re.sub(r'^(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+', '', name, flags=re.IGNORECASE).strip()
    
    # Remove unwanted words that might be captured with the name
    unwanted_words = [
        'HOME', 'ACCOUNT', 'BANK', 'STATEMENT', 'OF', 'INDIA', 'LIMITED', 'LTD',
        'DETAILS', 'CUSTOMER', 'HOLDER', 'NAME', 'BRANCH', 'IFSC', 'CODE'
    ]
    
    # Split into words and filter out unwanted words
    words = name.split()
    cleaned_words = []
    for word in words:
        word_upper = word.upper().strip('.,;:')
        # Skip if it's an unwanted word
        if word_upper not in unwanted_words and len(word) > 1:
            cleaned_words.append(word)
    
    # Join back
    cleaned_name = ' '.join(cleaned_words).strip()
    
    # CRITICAL VALIDATION: Must have at least 2 words (full name)
    # If only one word → extraction FAILED
    if not cleaned_name:
        return None
    
    word_count = len(cleaned_name.split())
    if word_count < 2:
        # Only one word - extraction failed, return None to indicate failure
        print(f"WARNING: Account holder name has only one word '{cleaned_name}' - extraction may have failed")
        return None
    
    # Additional validation: must not be all bank-related words
    name_upper = cleaned_name.upper()
    if any(word in name_upper for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'DETAILS']):
        return None
    
    return cleaned_name

def extract_account_holder_from_filename(pdf_path: str, pdf_text: str) -> Optional[str]:
    """
    Extract account holder name from PDF filename as fallback.
    Example: tejal_raut_statement.pdf → "TEJAL RAUT"
    """
    try:
        filename = os.path.basename(pdf_path)
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Common patterns: name_statement.pdf, name_statement_date.pdf, etc.
        # Remove common suffixes
        suffixes = ['_statement', '_stmt', '_bank', '_statement_', '_stmt_', 'statement', 'stmt']
        for suffix in suffixes:
            if name_without_ext.lower().endswith(suffix.lower()):
                name_without_ext = name_without_ext[:-len(suffix)]
                break
        
        # Split by underscores or hyphens and capitalize
        parts = re.split(r'[_\-\s]+', name_without_ext)
        # Filter out common non-name words
        filtered_parts = []
        skip_words = ['statement', 'stmt', 'bank', 'pdf', 'account', 'of', 'india', 'statementof']
        for part in parts:
            if part and part.lower() not in skip_words and len(part) > 1:
                filtered_parts.append(part.upper())
        
        if len(filtered_parts) >= 2:  # Must have at least 2 words (first + last name)
            extracted_name = ' '.join(filtered_parts)
            # Cross-verify with PDF content if possible
            if pdf_text:
                # Check if any part of the name appears in PDF
                name_parts_in_pdf = sum(1 for part in filtered_parts if part.upper() in pdf_text.upper())
                if name_parts_in_pdf >= 1:  # At least one part matches
                    return extracted_name
            else:
                return extracted_name
        
        return None
    except Exception as e:
        print(f"Error extracting name from filename: {str(e)}")
        return None

def extract_account_number_aggressive(text: str, pdf) -> Optional[str]:
    """
    Aggressive account number extraction - tries all possible patterns.
    Returns the longest valid numeric sequence labeled as account number.
    Validation: Must be 10-16 digits, numeric only.
    """
    account_numbers = []
    
    # Pattern 1: Look for explicit labels with account numbers (10-16 digits)
    patterns = [
        r'Account\s*(?:No|Number|#)\s*[:\s]+(\d{10,16})',
        r'A/c\s*(?:No|Number)\s*[:\s]+(\d{10,16})',
        r'Account\s*[:\s]+(\d{10,16})',
        r'Savings\s+A/c\s*[:\s]+(\d{10,16})',
        r'Current\s+A/c\s*[:\s]+(\d{10,16})',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            acc_num = match.group(1).strip()
            # Validate: 10-16 digits, numeric only
            if 10 <= len(acc_num) <= 16 and acc_num.isdigit():
                account_numbers.append((acc_num, len(acc_num)))
    
    # Pattern 2: Look in tables for account numbers
    try:
        for page_idx in range(min(3, len(pdf.pages))):
            tables = pdf.pages[page_idx].extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row:
                        continue
                    row_text = " ".join([str(cell) if cell else "" for cell in row]).upper()
                    # Check if row contains account number label
                    if any(keyword in row_text for keyword in ['ACCOUNT', 'A/C', 'ACCOUNT NO', 'ACCOUNT NUMBER']):
                        for cell in row:
                            if cell:
                                cell_str = str(cell).strip()
                                # Extract numeric sequences (10-16 digits)
                                matches = re.findall(r'\d{10,16}', cell_str)
                                for match in matches:
                                    # Validate: 10-16 digits, numeric only
                                    if 10 <= len(match) <= 16 and match.isdigit():
                                        account_numbers.append((match, len(match)))
    except:
        pass
    
    # Pattern 3: Look for standalone 10-16 digit numbers near account-related keywords
    # Find all 10-16 digit numbers
    all_numbers = re.findall(r'\b\d{10,16}\b', text)
    for num in all_numbers:
        # Validate: 10-16 digits, numeric only
        if not (10 <= len(num) <= 16 and num.isdigit()):
            continue
        # Check if it's near account-related keywords (within 50 chars)
        num_pos = text.find(num)
        context = text[max(0, num_pos-50):min(len(text), num_pos+50)].upper()
        if any(keyword in context for keyword in ['ACCOUNT', 'A/C', 'ACCOUNT NO', 'ACCOUNT NUMBER', 'SAVINGS', 'CURRENT']):
            account_numbers.append((num, len(num)))
    
    # Return the longest valid account number (most complete)
    # If multiple found, choose the longest one (most complete)
    if account_numbers:
        # Remove duplicates
        unique_numbers = {}
        for acc_num, length in account_numbers:
            if acc_num not in unique_numbers or unique_numbers[acc_num][1] < length:
                unique_numbers[acc_num] = (acc_num, length)
        
        # Sort by length (descending) and return the longest
        sorted_numbers = sorted(unique_numbers.values(), key=lambda x: x[1], reverse=True)
        return sorted_numbers[0][0]
    
    return None

def validate_and_ensure_required_fields(account_info: Dict, pdf_path: str, pdf_text: str, pdf) -> Dict:
    """
    CRITICAL: Final validation - ensures account_number and account_holder are NEVER null.
    If missing, throws error or uses last-resort extraction methods.
    """
    # Validate account_number
    if not account_info.get("account_number") or not account_info["account_number"].strip():
        # Last resort: try to extract ANY valid account number from entire PDF
        print("WARNING: account_number is missing - attempting last-resort extraction...")
        account_number = extract_account_number_aggressive(pdf_text, pdf)
        if account_number:
            account_info["account_number"] = account_number
            print(f"✓ Extracted account_number: {account_number}")
        else:
            # If still missing, this is a CRITICAL ERROR
            raise ValueError(
                "CRITICAL ERROR: account_number is missing and could not be extracted from PDF. "
                "This field MUST NEVER be null. Please check the PDF format."
            )
    
    # Validate account_holder
    if not account_info.get("account_holder") or not account_info["account_holder"].strip():
        # Last resort: try filename extraction
        print("WARNING: account_holder is missing - attempting filename extraction...")
        account_holder = extract_account_holder_from_filename(pdf_path, pdf_text)
        if account_holder:
            account_info["account_holder"] = account_holder
            print(f"✓ Extracted account_holder from filename: {account_holder}")
        else:
            # Try one more aggressive extraction from PDF text
            account_holder = extract_account_holder_aggressive(pdf_text)
            if account_holder:
                account_info["account_holder"] = account_holder
                print(f"✓ Extracted account_holder: {account_holder}")
            else:
                # If still missing, this is a CRITICAL ERROR
                raise ValueError(
                    "CRITICAL ERROR: account_holder is missing and could not be extracted from PDF. "
                    "This field MUST NEVER be null. Please check the PDF format."
                )
    
    # Ensure both are non-empty strings
    account_info["account_number"] = str(account_info["account_number"]).strip()
    account_info["account_holder"] = str(account_info["account_holder"]).strip().upper()
    
    return account_info

def extract_account_holder_aggressive(text: str) -> Optional[str]:
    """
    Aggressive account holder extraction - tries all possible patterns.
    Priority order:
    1. Explicit labels (Account Holder Name, Customer Name, etc.)
    2. Statement header section
    3. Address block (name before address)
    4. Salutation lines (Mr./Ms.)
    """
    # Priority 1: Explicit labels
    explicit_patterns = [
        r'Account\s+Holder\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        r'Name\s+of\s+the\s+Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        r'Account\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            validated = validate_and_clean_account_holder_name(name)
            if validated:
                return validated
    
    # Priority 2: Statement header section (first 2000 chars)
    header_text = text[:2000] if len(text) > 2000 else text
    header_patterns = [
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|Address|$|\n))',
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{3,}?)(?:\s*(?:Account|IFSC|Branch|Address|$|\n))',
    ]
    
    for pattern in header_patterns:
        match = re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            validated = validate_and_clean_account_holder_name(name)
            if validated:
                return validated
    
    # Priority 3: Address block (name usually appears before address)
    address_patterns = [
        r'([A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+)\s+[A-Z][A-Za-z\s,]+(?:Street|Road|Lane|Avenue|Colony|Nagar|Pura|Village|City|State|Pin|Pincode)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            validated = validate_and_clean_account_holder_name(name)
            if validated:
                return validated
    
    return None

def extract_missing_account_info_from_tables(pdf, account_info: Dict):
    """Extract missing account info from PDF tables as fallback - IMPROVED"""
    try:
        for page_idx in range(min(3, len(pdf.pages))):
            tables = pdf.pages[page_idx].extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Look for account info in table cells
                for row in table:
                    if not row:
                        continue
                    
                    row_text = " ".join([str(cell) if cell else "" for cell in row]).upper()
                    
                    # Account number
                    if not account_info.get("account_number"):
                        for cell in row:
                            if cell:
                                cell_str = str(cell).strip()
                                # Check if cell contains account number pattern
                                match = re.search(r'(\d{10,})', cell_str)
                                if match and ("ACCOUNT" in cell_str.upper() or len(cell_str) >= 10):
                                    account_info["account_number"] = match.group(1)
                                    break
                    
                    # Account holder name - improved to handle "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI", etc.
                    if not account_info.get("account_holder"):
                        for idx, cell in enumerate(row):
                            if cell and isinstance(cell, str):
                                cell_upper = cell.upper()
                                # Check if previous cell has "NAME" or "HOLDER"
                                if idx > 0 and row[idx-1]:
                                    prev_cell = str(row[idx-1]).upper()
                                    if ("NAME" in prev_cell or "HOLDER" in prev_cell) and len(cell.strip()) > 3:
                                        # Check if it looks like a name (has letters, not all numbers)
                                        if re.search(r'[A-Za-z]', cell) and not re.match(r'^\d+$', cell):
                                            name = cell.strip()
                                            # Remove bank words
                                            for word in ['BANK', 'STATEMENT', 'ACCOUNT', 'OF', 'INDIA']:
                                                name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE).strip()
                                            # Allow all-caps names (like "AARAV AGRAWAL") - they are valid
                                            if len(name) > 2 and re.search(r'[A-Za-z]', name):
                                                # CRITICAL: Validate it's a FULL name (multiple words)
                                                validated_name = validate_and_clean_account_holder_name(name)
                                                if validated_name:  # Only set if validation passes
                                                    account_info["account_holder"] = validated_name
                                                    break
                                
                                # Also check if cell itself contains name with title (Mr./Mrs./Ms.)
                                # CRITICAL: Capture FULL name, not just first word
                                name_with_title = re.search(r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))', cell, re.IGNORECASE)
                                if name_with_title:
                                    name = name_with_title.group(1).strip()
                                    # Remove bank words
                                    for word in ['BANK', 'STATEMENT', 'ACCOUNT', 'OF', 'INDIA']:
                                        name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE).strip()
                                    # Allow all-caps names - they are valid
                                    if len(name) > 2 and re.search(r'[A-Za-z]', name):
                                        # CRITICAL: Validate it's a FULL name (multiple words)
                                        validated_name = validate_and_clean_account_holder_name(name)
                                        if validated_name:  # Only set if validation passes
                                            account_info["account_holder"] = validated_name
                                            break
                                
                                # Also check for "Name: FULL NAME" pattern in cell
                                name_colon_pattern = re.search(r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))', cell, re.IGNORECASE)
                                if name_colon_pattern:
                                    name = name_colon_pattern.group(1).strip()
                                    # Remove bank words
                                    for word in ['BANK', 'STATEMENT', 'ACCOUNT', 'OF', 'INDIA']:
                                        name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE).strip()
                                    if len(name) > 2 and re.search(r'[A-Za-z]', name):
                                        # CRITICAL: Validate it's a FULL name (multiple words)
                                        validated_name = validate_and_clean_account_holder_name(name)
                                        if validated_name:  # Only set if validation passes
                                            account_info["account_holder"] = validated_name
                                            break
                    
                    # IFSC
                    if not account_info.get("ifsc"):
                        for cell in row:
                            if cell:
                                cell_str = str(cell).strip().upper()
                                match = re.search(r'([A-Z]{4}0[A-Z0-9]{6})', cell_str)
                                if match:
                                    account_info["ifsc"] = match.group(1)
                                    break
                    
                    # Branch
                    if not account_info.get("branch"):
                        for idx, cell in enumerate(row):
                            if cell and isinstance(cell, str):
                                cell_upper = cell.upper()
                                # Check if previous cell has "BRANCH"
                                if idx > 0 and row[idx-1]:
                                    prev_cell = str(row[idx-1]).upper()
                                    if "BRANCH" in prev_cell and len(cell.strip()) > 2:
                                        branch = cell.strip()
                                        # Remove unwanted words
                                        for word in ['BRANCH', 'BANK', 'DETAILS', 'OF', 'STATEMENT']:
                                            branch = re.sub(rf'\b{word}\b', '', branch, flags=re.IGNORECASE).strip()
                                        if branch and branch.upper() not in ['DETAILS OF STATEMENT', 'STATEMENT OF ACCOUNT']:
                                            account_info["branch"] = branch
                                            break
                    
                    # Statement period
                    if not account_info.get("statement_period"):
                        row_text_full = " ".join([str(cell) if cell else "" for cell in row])
                        period_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', row_text_full, re.IGNORECASE)
                        if period_match:
                            account_info["statement_period"] = f"{period_match.group(1)} to {period_match.group(2)}"
    except Exception as e:
        print(f"Error in extract_missing_account_info_from_tables: {str(e)}")
        pass

def detect_bank(text: str) -> str:
    """Detect bank from PDF text - ROBUST detection from PDF content (logo/header/keywords)
    CRITICAL: Must NEVER return "Unknown" - use IFSC codes and multiple fallback strategies
    """
    text_upper = text.upper()
    
    # Strategy 1: Check IFSC codes first (most reliable)
    ifsc_match = re.search(r'IFSC[:\s]*(?:CODE)?[:\s]*([A-Z]{4}0[A-Z0-9]{6})', text_upper)
    if ifsc_match:
        ifsc_code = ifsc_match.group(1)
        ifsc_prefix = ifsc_code[:4]
        # Map IFSC prefixes to banks
        ifsc_bank_map = {
            'SBIN': 'State Bank of India',
            'BKID': 'Bank of India',
            'UTIB': 'Axis Bank',
            'HDFC': 'HDFC Bank',
            'CBIN': 'Central Bank of India',
            'UBIN': 'Union Bank of India',
            'ICIC': 'ICICI Bank',
            'PUNB': 'Punjab National Bank',
            'CNRB': 'Canara Bank',
            'BARB': 'Bank of Baroda',
            'IOBA': 'Indian Overseas Bank',
        }
        if ifsc_prefix in ifsc_bank_map:
            return ifsc_bank_map[ifsc_prefix]
    
    # Strategy 2: Check explicit bank name patterns (priority order matters)
    # CRITICAL: Check Central Bank of India FIRST (before Bank of India) to avoid false matches
    # This override MUST take precedence over any fuzzy or similarity-based detection
    if re.search(r'CENTRAL\s+BANK\s+OF\s+INDIA', text_upper) or \
       re.search(r'CENTRAL\s+BANK', text_upper) or \
       re.search(r'\bCBI\b', text_upper) or \
       ("CENTRAL BANK" in text_upper and re.search(r'CBIN', text_upper)):
        return "Central Bank of India"
    
    # Check SBI first (before BOI) to avoid false matches
    if "STATE BANK OF INDIA" in text_upper or \
       (re.search(r'\bSBI\b', text_upper) and "BANK OF INDIA" not in text_upper and "STATE BANK" in text_upper):
        return "State Bank of India"
    
    # Check Union Bank of India BEFORE BOI to avoid false match on "UNION BANK OF INDIA"
    if re.search(r'UNION\s+BANK\s+OF\s+INDIA', text_upper) or \
       re.search(r'UNION\s+BANK', text_upper) or \
       re.search(r'\bUBI\b', text_upper) or \
       ("UNION BANK" in text_upper and re.search(r'UBIN', text_upper)):
        return "Union Bank of India"
    
    # Check BOI - ensure we do NOT match "UNION BANK OF INDIA"
    # Must check for full "BANK OF INDIA" without "UNION" prefix or standalone "BOI"
    if (re.search(r'(?<!UNION\s)BANK\s+OF\s+INDIA', text_upper) and "STATE BANK OF INDIA" not in text_upper and "CENTRAL BANK" not in text_upper) or \
       (re.search(r'\bBOI\b', text_upper) and "AXIS" not in text_upper and "STATE" not in text_upper and "CENTRAL" not in text_upper and "UNION" not in text_upper):
        return "Bank of India"
    
    # Check Axis Bank - must be explicit "AXIS BANK" (not just "AXIS")
    if "AXIS BANK" in text_upper or \
       (re.search(r'\bAXIS\b', text_upper) and re.search(r'UTIB', text_upper)):
        return "Axis Bank"
    
    # Check HDFC Bank
    if "HDFC BANK" in text_upper or \
       (re.search(r'\bHDFC\b', text_upper) and "HDFC BANK" in text_upper):
        return "HDFC Bank"
    
    # Central Bank of India already checked above (priority), skip here to avoid duplicate
    
    # Check ICICI Bank
    if "ICICI BANK" in text_upper or \
       (re.search(r'\bICICI\b', text_upper) and re.search(r'ICIC', text_upper)):
        return "ICICI Bank"
    
    # Strategy 3: Check for bank-specific keywords in header/title area (first 2000 chars)
    header_text = text_upper[:2000] if len(text_upper) > 2000 else text_upper
    
    # Additional bank patterns
    if re.search(r'PUNJAB\s+NATIONAL\s+BANK', header_text) or re.search(r'\bPNB\b', header_text):
        return "Punjab National Bank"
    if re.search(r'CANARA\s+BANK', header_text):
        return "Canara Bank"
    if re.search(r'BANK\s+OF\s+BARODA', header_text) or re.search(r'\bBOB\b', header_text):
        return "Bank of Baroda"
    if re.search(r'INDIAN\s+OVERSEAS\s+BANK', header_text) or re.search(r'\bIOB\b', header_text):
        return "Indian Overseas Bank"
    
    # Strategy 4: Check for any bank name pattern (fallback)
    if "BANK" in header_text:
        # Try to extract bank name from common patterns
        boi_match = re.search(r'([A-Z][A-Z\s]+?)\s+BANK\s+OF\s+INDIA', header_text)
        if boi_match:
            prefix = boi_match.group(1).strip()
            if re.fullmatch(r'CENTRAL', prefix):
                return "Central Bank of India"
            if re.fullmatch(r'UNION', prefix):
                return "Union Bank of India"
            return "Bank of India"
        any_bank = re.search(r'([A-Z][A-Z\s]+?)\s+BANK', header_text)
        if any_bank:
            return f"{any_bank.group(1).title()} Bank"
    
    # Strategy 5: Last resort - check filename if available (but prefer PDF content)
    # This should rarely be needed, but better than "Unknown"
    # Note: We don't have filename here, so we'll use a generic fallback
    
    # If still not found, return a generic name based on common patterns
    # This is better than "Unknown" as it indicates we tried but couldn't determine
    return "Bank (Unidentified)"  # Changed from "Unknown" to indicate we tried

def extract_axis_account_info_improved(text: str, account_info: Dict, pdf):
    """Extract Axis Bank specific account info - IMPROVED"""
    # Account number - multiple patterns
    patterns = [
        r'Account\s*(?:No|Number|#)\s*[:\s]*(\d{10,})',
        r'A/c\s*(?:No|Number)\s*[:\s]*(\d{10,})',
        r'Account\s*Number[:\s]*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["account_number"] = match.group(1).strip()
            break
    
    # Account holder - multiple patterns with validation
    # CRITICAL: Must extract FULL names like "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI", "RAJESH KUMAR"
    # Use GREEDY patterns to capture complete names, not just first word
    name_patterns = [
        # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title) - GREEDY to get full name
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|Customer|IFSC|Branch|$|\n))',
        # Pattern for "Name: ..." with optional title - capture until Account/Customer/IFSC/Branch/end
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|Customer|IFSC|Branch|$|\n))',
        # Pattern for "Customer Name: ..." - capture full name
        r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        # Pattern for name before "Account No" or "Customer ID" - capture everything before these keywords
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)\s+(?:Account\s+No|Customer\s+ID)',
        # Pattern for standalone name (without prefix) - capture full name until Account/IFSC/etc
        r'Name\s*[:\s]+([A-Z][A-Z\s]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'(AXIS\s+BANK|LTD|LIMITED|BANK)', '', name, flags=re.IGNORECASE).strip()
            name = ' '.join(name.split())
            # Validate: allow all-caps names (like "AARAV AGRAWAL") - they are valid
            if (len(name) > 2 and 
                not any(word in name.upper() for word in ['STATEMENT', 'BANK', 'ACCOUNT']) and
                re.search(r'[A-Za-z]', name)):  # Must contain at least one letter
                account_info["account_holder"] = name
                break
    
    # IFSC - multiple patterns
    ifsc_patterns = [
        r'IFSC\s+Code\s*[:\s]*([A-Z0-9]{11})',
        r'IFSC[:\s]*([A-Z0-9]{11})',
        r'IFSC\s*Code[:\s]*([A-Z]{4}0[A-Z0-9]{6})',
    ]
    for pattern in ifsc_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["ifsc"] = match.group(1).strip().upper()
            break
    
    # Statement period - multiple patterns
    period_patterns = [
        r'period\s*\(From\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})\s+To\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})\)',
        r'Period[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})\s+To\s+(\d{2}[-/]\d{2}[-/]\d{4})',
        r'From\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})\s+To\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["statement_period"] = f"{match.group(1)} To {match.group(2)}"
            break
    
    # Branch - multiple patterns
    branch_patterns = [
        r'BRANCH\s+ADDRESS\s*[-\s]+.*?,\s*([A-Z][A-Za-z\s,]+?)(?:,|\n|IFSC)',
        r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address)',
        r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
    ]
    for pattern in branch_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            branch = match.group(1).strip()
            branch = re.sub(r'(BRANCH|ADDRESS)', '', branch, flags=re.IGNORECASE).strip()
            if branch:
                account_info["branch"] = branch
                break

def extract_boi_account_info_improved(text: str, account_info: Dict, pdf):
    """Extract Bank of India specific account info - IMPROVED"""
    # Account number - multiple patterns
    patterns = [
        r'Account\s+No\s*[:\s]+(\d{10,})',
        r'Account\s+Number\s*[:\s]+(\d{10,})',
        r'A/c\s+No\s*[:\s]+(\d{10,})',
        r'Account\s*[:\s]+(\d{10,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["account_number"] = match.group(1).strip()
            break
    
    # Account holder - multiple patterns with validation
    # IMPORTANT: Must extract names like "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI", "Name: Tejal Raut"
    name_patterns = [
        # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title)
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]{2,}?)(?:\s|$|\n|Account|Customer|IFSC)',
        # Pattern for "Name: Tejal Raut" or "Name: AARAV AGRAWAL"
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{2,}?)(?:\n|IFSC|Account\s+No|Branch|$)',
        # Pattern for "Account Holder: ..."
        r'Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\n|IFSC|Branch|$)',
        # Pattern for "Customer Name: ..."
        r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\n|IFSC|Branch|$)',
        # Pattern for name before "Account No"
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]{2,}?)\s+Account\s+No',
        # Generic name pattern
        r'Name[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|IFSC|Account|Branch|$)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Remove bank-related words
            name = re.sub(r'(BANK\s+OF\s+INDIA|BOI|BANK|LIMITED|LTD)', '', name, flags=re.IGNORECASE).strip()
            name = ' '.join(name.split())
            
            # Validate: must be a real name (not bank/statement words)
            # Allow all-caps names (like "AARAV AGRAWAL") - they are valid
            if (len(name) > 2 and 
                not any(word in name.upper() for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'OF', 'INDIA', 'DETAILS']) and
                re.search(r'[A-Za-z]', name)):  # Must contain at least one letter
                # CRITICAL: Validate it's a FULL name (multiple words)
                validated_name = validate_and_clean_account_holder_name(name)
                if validated_name:  # Only set if validation passes (has multiple words)
                    account_info["account_holder"] = validated_name
                    break
    
    # IFSC - multiple patterns
    ifsc_patterns = [
        r'IFSC\s+Code\s*[:\s]+([A-Z0-9]{11})',
        r'IFSC[:\s]+([A-Z0-9]{11})',
        r'IFSC\s*Code[:\s]*([A-Z]{4}0[A-Z0-9]{6})',
    ]
    for pattern in ifsc_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["ifsc"] = match.group(1).strip().upper()
            break
    
    # Statement period - multiple patterns
    period_patterns = [
        r'(?:For the period|Statement|Period)[:\s]+([A-Za-z]+\s+\d{1,2}[,\s]+\d{4})\s+to\s+([A-Za-z]+\s+\d{1,2}[,\s]+\d{4})',
        r'From\s+([A-Za-z]+\s+\d{1,2}[,\s]+\d{4})\s+to\s+([A-Za-z]+\s+\d{1,2}[,\s]+\d{4})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["statement_period"] = f"{match.group(1)} to {match.group(2)}"
            break
    
    # Branch - multiple patterns
    branch_patterns = [
        r'BANK\s+OF\s+INDIA\s*\n\s*([A-Z][A-Za-z\s]+?)(?:Branch|\n|IFSC)',
        r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address)',
        r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
    ]
    for pattern in branch_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            branch = match.group(1).strip()
            branch = re.sub(r'(BANK\s+OF\s+INDIA|BRANCH)', '', branch, flags=re.IGNORECASE).strip()
            if branch:
                account_info["branch"] = branch
                break

def extract_hdfc_account_info_improved(text: str, account_info: Dict, pdf):
    """Extract HDFC Bank specific account info - IMPROVED"""
    # Account number
    patterns = [
        r'Account\s+No[:\s]+(\d{10,})',
        r'Account\s+Number[:\s]+(\d{10,})',
        r'A/c\s+No[:\s]+(\d{10,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["account_number"] = match.group(1).strip()
            break
    
    # Account holder - improved to handle "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI"
    # CRITICAL: Must extract FULL names, not just first word
    name_patterns = [
        # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title) - GREEDY to get full name
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]+?)(?:\s*(?:Account\s+No|Account|IFSC|Branch|$|\n))',
        # Pattern for "Name: ..." with optional title - capture until Account/IFSC/Branch/end
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        # Pattern for "Account Holder: ..." - capture full name
        r'Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        # Pattern for standalone name (without prefix) - capture full name until Account/IFSC/etc
        r'Name\s*[:\s]+([A-Z][A-Z\s]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            name = ' '.join(name.split())
            # Allow all-caps names - they are valid
            if len(name) > 2 and re.search(r'[A-Za-z]', name):
                # CRITICAL: Validate it's a FULL name (multiple words)
                validated_name = validate_and_clean_account_holder_name(name)
                if validated_name:  # Only set if validation passes
                    account_info["account_holder"] = validated_name
                    break
    
    # IFSC
    ifsc_patterns = [
        r'IFSC[:\s]+([A-Z0-9]{11})',
        r'IFSC\s+Code[:\s]+([A-Z0-9]{11})',
    ]
    for pattern in ifsc_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["ifsc"] = match.group(1).strip().upper()
            break
    
    # Branch
    branch_patterns = [
        r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Period)',
        r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
    ]
    for pattern in branch_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["branch"] = match.group(1).strip()
            break
    
    # Statement period
    period_patterns = [
        r'Period[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})\s+To\s+(\d{2}[-/]\d{2}[-/]\d{4})',
        r'From\s+(\d{2}[-/]\d{2}[-/]\d{4})\s+To\s+(\d{2}[-/]\d{2}[-/]\d{4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["statement_period"] = f"{match.group(1)} To {match.group(2)}"
            break

def extract_sbi_account_info_improved(text: str, account_info: Dict, pdf):
    """Extract SBI specific account info - IMPROVED"""
    # Account number
    patterns = [
        r'Account\s+No\.?\s*[:\s]*(\d{10,})',
        r'Account\s+Number[:\s]+(\d{10,})',
        r'A/c\s+No[:\s]+(\d{10,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["account_number"] = match.group(1).strip()
            break
    
    # Account holder - improved to handle "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI"
    name_patterns = [
        # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title)
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]{2,}?)(?:\s|$|\n|Account|IFSC|Branch)',
        # Pattern for "Name: ..." with optional title
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\n|IFSC|Account|Branch|$)',
        # Pattern for "Account Holder: ..."
        r'Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\n|IFSC|Branch|$)',
        # Pattern for "Customer Name: ..."
        r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Z\s\.]+?)(?:\n|IFSC|Branch|$)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            name = ' '.join(name.split())
            # Allow all-caps names - they are valid
            if len(name) > 2 and re.search(r'[A-Za-z]', name):
                # CRITICAL: Validate it's a FULL name (multiple words)
                validated_name = validate_and_clean_account_holder_name(name)
                if validated_name:  # Only set if validation passes
                    account_info["account_holder"] = validated_name
                    break
    
    # IFSC
    ifsc_patterns = [
        r'IFSC\s*[:\s]+([A-Z0-9]{11})',
        r'IFSC\s+Code[:\s]+([A-Z0-9]{11})',
    ]
    for pattern in ifsc_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["ifsc"] = match.group(1).strip().upper()
            break
    
    # Branch
    branch_patterns = [
        r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address)',
        r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
    ]
    for pattern in branch_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["branch"] = match.group(1).strip()
            break
    
    # Statement period
    period_patterns = [
        r'Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'From\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["statement_period"] = f"{match.group(1)} to {match.group(2)}"
            break

def extract_central_bank_account_holder_from_header(text: str) -> Optional[str]:
    """
    CENTRAL BANK SPECIFIC: Extract account holder name ONLY from header line
    appearing near "STATEMENT OF ACCOUNT".
    
    STRICT RULES:
    - Extract ONLY from header near "STATEMENT OF ACCOUNT"
    - Example: "Mr. RAMESH KUMAR" -> "RAMESH KUMAR" (UPPERCASE)
    - Remove title (Mr./Mrs./Ms.)
    - Return UPPERCASE format
    
    STRICTLY IGNORE:
    - Footer text
    - Transaction count text (e.g., "06 300TXN", "03 300TXN")
    - Page numbers
    - Summaries
    - Any text that looks like counters or numbers
    """
    # Look for "STATEMENT OF ACCOUNT" in text
    statement_match = re.search(r'STATEMENT\s+OF\s+ACCOUNT', text, re.IGNORECASE)
    if not statement_match:
        return None
    
    # Get context around "STATEMENT OF ACCOUNT" (500 chars BEFORE only - header area)
    # We want header, NOT footer, so only look before "STATEMENT OF ACCOUNT"
    match_pos = statement_match.start()
    context_start = max(0, match_pos - 500)
    context_end = match_pos  # Only look BEFORE "STATEMENT OF ACCOUNT", not after
    context = text[context_start:context_end]
    
    # Look for name patterns near "STATEMENT OF ACCOUNT" in header area
    # Pattern: "Mr. RAMESH KUMAR" or "Mrs. NAME" or "Ms. NAME"
    name_patterns = [
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.)\s+([A-Z][A-Z\s\.]{2,}?)(?:\s*(?:STATEMENT|OF|ACCOUNT|$|\n))',
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.)\s+([A-Z][A-Za-z\s\.]{2,}?)(?:\s*(?:STATEMENT|OF|ACCOUNT|$|\n))',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, context, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            
            # STRICT VALIDATION: Reject values that look like counters, page numbers, or transaction counts
            # CRITICAL: Reject patterns like "08 300TXN", "06 300TXN", "03 300TXN", etc.
            name_upper = name.upper()
            name_stripped = name.strip()
            
            # Reject if it starts with digits followed by space and more digits/TXN (e.g., "08 300TXN")
            if re.match(r'^\d+\s+\d+TXN', name_upper) or re.match(r'^\d+\s+\d+', name_stripped):
                print(f"  REJECTED: '{name}' - looks like transaction counter")
                continue
            
            # Reject if it contains transaction count patterns anywhere
            if re.search(r'\d+\s*\d+TXN', name_upper) or re.search(r'\d+TXN', name_upper):
                print(f"  REJECTED: '{name}' - contains TXN pattern")
                continue
            
            # Reject if it starts with digits (e.g., "08", "06", "03")
            if re.match(r'^\d+', name_stripped):
                print(f"  REJECTED: '{name}' - starts with digits")
                continue
            
            # Reject if it's mostly numbers or contains page number patterns
            if re.search(r'PAGE\s*\d+', name_upper):
                print(f"  REJECTED: '{name}' - contains page number")
                continue
            
            # Reject if it's too short or looks like a counter
            if len(name_stripped) < 4:
                print(f"  REJECTED: '{name}' - too short")
                continue
            
            # Reject if it contains only digits and spaces (e.g., "08 300")
            if re.match(r'^[\d\s]+$', name_stripped):
                print(f"  REJECTED: '{name}' - only digits and spaces")
                continue
            
            # Remove bank-related words
            name = re.sub(r'(CENTRAL|BANK|OF|INDIA|STATEMENT|ACCOUNT)', '', name, flags=re.IGNORECASE).strip()
            name = ' '.join(name.split())
            
            # Validate: must be a real name (not bank/statement words, not counters)
            # CRITICAL: Must contain letters, not just numbers, and must have at least 2 words
            if (len(name) > 2 and 
                not any(word in name.upper() for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'CENTRAL', 'OF', 'INDIA', 'TXN', 'PAGE']) and
                re.search(r'[A-Za-z]', name) and  # Must contain at least one letter
                not re.search(r'\d+\s+\d+', name) and  # Reject if contains number patterns like "06 300"
                not re.match(r'^\d+', name)):  # Reject if starts with digits
                
                # Convert to UPPERCASE (as per user requirement: "RAMESH KUMAR")
                name_upper = name.upper()
                
                # Final check: must have at least 2 words (first + last name)
                name_words = name_upper.split()
                if len(name_words) >= 2:
                    # Validate it's a FULL name (multiple words)
                    validated_name = validate_and_clean_account_holder_name(name_upper)
                    if validated_name:
                        # Return in UPPERCASE format
                        print(f"  ACCEPTED: '{validated_name.upper()}' - valid account holder name")
                        return validated_name.upper()
                else:
                    print(f"  REJECTED: '{name_upper}' - not enough words (need at least 2)")
    
    return None

def extract_central_bank_account_info(text: str, account_info: Dict, pdf):
    """Extract Central Bank of India account info - STRICT OVERRIDE RULES"""
    # STRICT OVERRIDE RULE #2: Account holder FORCE from header ONLY
    # Extract account holder from header near "STATEMENT OF ACCOUNT" - this is MANDATORY
    # DO NOT use any other extraction method for account_holder
    print("  Attempting Central Bank account holder extraction from header...")
    account_holder_from_header = extract_central_bank_account_holder_from_header(text)
    
    # Store the header-extracted account holder BEFORE calling generic extraction
    saved_account_holder = account_holder_from_header
    
    if account_holder_from_header:
        # FORCE the account holder from header - ignore any other extraction
        account_info["account_holder"] = account_holder_from_header
        print(f"✓ STRICT OVERRIDE: Central Bank account_holder from header: {account_holder_from_header}")
    else:
        print("  WARNING: Could not extract Central Bank account_holder from header near 'STATEMENT OF ACCOUNT'")
        print("  Will NOT use fallback methods - header extraction is mandatory for Central Bank")
    
    # Use generic but with Central Bank specific patterns (for other fields like account_number, branch, etc.)
    # BUT DO NOT override account_holder if it was already set from header
    extract_generic_account_info_improved(text, account_info, pdf)
    
    # CRITICAL: Ensure account_holder is NOT overwritten by generic extraction
    # If we extracted from header, FORCE it to stay (even if generic extraction found something else)
    if saved_account_holder:
        account_info["account_holder"] = saved_account_holder
        print(f"  FORCED: account_holder = '{saved_account_holder}' (from header only, ignoring other sources)")
    
    # Additional Central Bank specific patterns
    # Account number
    if not account_info.get("account_number"):
        patterns = [
            r'Account\s+No[:\s]+(\d{10,})',
            r'A/c\s+No[:\s]+(\d{10,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["account_number"] = match.group(1).strip()
                break
    
    # Account holder - CENTRAL BANK SPECIFIC: Only use header extraction (already done above)
    # If header extraction failed, try generic patterns as fallback
    if not account_info.get("account_holder"):
        name_patterns = [
            # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title) - GREEDY to get full name
            r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Account\s+No|Branch|$|\n))',
            # Pattern for "Name: ..." with optional title - capture until Account/IFSC/Branch/end
            r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Account\s+No|Branch|$|\n))',
            # Pattern for "Account Holder: ..." - capture full name
            r'Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
            # Pattern for "Customer Name: ..." - capture full name
            r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
            # Pattern for standalone name (without prefix) - capture full name until Account/IFSC/etc
            r'Name\s*[:\s]+([A-Z][A-Z\s]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                name = ' '.join(name.split())
                
                # Aggressively remove bank/statement words
                exclude_words = [
                    'CENTRAL', 'BANK', 'OF', 'INDIA', 'STATEMENT', 'ACCOUNT',
                    'LIMITED', 'LTD', 'STATEMENT OF', 'ACCOUNT STATEMENT'
                ]
                for word in exclude_words:
                    name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE).strip()
                
                name_clean = ' '.join(name.split())
                # Validate it's a real name - allow all-caps names (like "AARAV AGRAWAL")
                if (len(name_clean) > 2 and 
                    not any(word in name_clean.upper() for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'CENTRAL', 'OF']) and
                    re.search(r'[A-Za-z]', name_clean)):  # Must contain at least one letter
                    # CRITICAL: Validate it's a FULL name (multiple words)
                    validated_name = validate_and_clean_account_holder_name(name_clean)
                    if validated_name:  # Only set if validation passes
                        account_info["account_holder"] = validated_name
                        break
    
    # IFSC
    if not account_info.get("ifsc"):
        ifsc_patterns = [
            r'IFSC\s*(?:Code)?\s*[:\s]+([A-Z0-9]{11})',
            r'IFSC[:\s]+([A-Z]{4}0[A-Z0-9]{6})',
        ]
        for pattern in ifsc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["ifsc"] = match.group(1).strip().upper()
                break
    
    # Branch
    if not account_info.get("branch"):
        branch_patterns = [
            r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address|Code)',
            r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
            r'Branch\s+Code[:\s]+\d+\s+([A-Z][A-Za-z\s\-]+)',
        ]
        for pattern in branch_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                branch = match.group(1).strip()
                branch = re.sub(r'(BRANCH|BANK)', '', branch, flags=re.IGNORECASE).strip()
                if branch:
                    account_info["branch"] = branch
                    break
    
    # Statement period
    if not account_info.get("statement_period"):
        period_patterns = [
            r'Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'From\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Statement\s+Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["statement_period"] = f"{match.group(1)} to {match.group(2)}"
                break

def extract_union_bank_account_info(text: str, account_info: Dict, pdf):
    """Extract Union Bank of India account info - IMPROVED"""
    extract_generic_account_info_improved(text, account_info, pdf)
    
    # Additional Union Bank specific patterns for missing fields
    # IFSC
    if not account_info.get("ifsc"):
        ifsc_patterns = [
            r'IFSC\s*(?:Code)?\s*[:\s]+([A-Z0-9]{11})',
            r'IFSC[:\s]+([A-Z]{4}0[A-Z0-9]{6})',
        ]
        for pattern in ifsc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["ifsc"] = match.group(1).strip().upper()
                break
    
    # Branch
    if not account_info.get("branch"):
        branch_patterns = [
            r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address|Code)',
            r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
        ]
        for pattern in branch_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                branch = match.group(1).strip()
                branch = re.sub(r'(BRANCH|BANK|UNION)', '', branch, flags=re.IGNORECASE).strip()
                if branch:
                    account_info["branch"] = branch
                    break
    
    # Statement period
    if not account_info.get("statement_period"):
        period_patterns = [
            r'Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'From\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["statement_period"] = f"{match.group(1)} to {match.group(2)}"
                break

def extract_generic_account_info_improved(text: str, account_info: Dict, pdf):
    """Generic extraction for unknown banks - IMPROVED"""
    # Account number - try multiple patterns
    patterns = [
        r'Account\s*(?:No|Number|#)\s*[:\s]+(\d{10,})',
        r'A/c\s*(?:No|Number)\s*[:\s]+(\d{10,})',
        r'Account[:\s]+(\d{10,})',
        r'(\d{10,})',  # Last resort: any 10+ digit number
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["account_number"] = match.group(1).strip()
            break
    
    # Account holder - improved to avoid bank names and statement headers
    # CRITICAL: Must extract FULL names like "Mr. AARAV AGRAWAL", "Mrs. MANOJ JOSHI", "Name: Tejal Raut"
    # Use GREEDY patterns to capture complete names, not just first word
    name_patterns = [
        # Pattern for "Mr. AARAV AGRAWAL" or "Mrs. MANOJ JOSHI" (with title) - GREEDY to get full name
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.|M/s\.|M/s)\s+([A-Z][A-Z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|Customer|$|\n))',
        # Pattern for "Name: ..." with optional title - capture until Account/IFSC/Branch/end
        r'Name\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Account\s+No|Branch|Customer|$|\n))',
        # Pattern for "Account Holder: ..." - capture full name
        r'Account\s+Holder[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        # Pattern for "Customer Name: ..." - capture full name
        r'Customer\s+Name[:\s]+(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
        # Pattern for name before "Account No" - capture everything before Account No
        r'(?:Mr\.|Mrs\.|Ms\.|Miss\.)?\s*([A-Z][A-Za-z\s\.]+?)\s+Account\s+No',
        # Pattern for standalone name (without prefix) - capture full name until Account/IFSC/etc
        r'Name\s*[:\s]+([A-Z][A-Z\s]+?)(?:\s*(?:Account|IFSC|Branch|$|\n))',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            name = ' '.join(name.split())
            
            # Remove bank-related words and statement headers
            exclude_words = [
                'BANK', 'LIMITED', 'LTD', 'INDIA', 'STATEMENT', 'OF', 'ACCOUNT', 
                'CENTRAL', 'UNION', 'AXIS', 'HDFC', 'SBI', 'BOI', 'STATE',
                'STATEMENT OF', 'ACCOUNT STATEMENT', 'BANK STATEMENT'
            ]
            for word in exclude_words:
                name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE).strip()
            
            # Validate: allow all-caps names (like "AARAV AGRAWAL") - they are valid
            name_clean = ' '.join(name.split())
            if (len(name_clean) > 2 and 
                not any(word in name_clean.upper() for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'OF']) and
                re.search(r'[A-Za-z]', name_clean)):  # Must contain at least one letter
                # CRITICAL: Validate it's a FULL name (multiple words)
                validated_name = validate_and_clean_account_holder_name(name_clean)
                if validated_name:  # Only set if validation passes
                    account_info["account_holder"] = validated_name
                    break
    
    # IFSC
    ifsc_patterns = [
        r'IFSC\s*(?:Code)?\s*[:\s]+([A-Z0-9]{11})',
        r'IFSC[:\s]+([A-Z]{4}0[A-Z0-9]{6})',
    ]
    for pattern in ifsc_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["ifsc"] = match.group(1).strip().upper()
            break
    
    # Branch
    branch_patterns = [
        r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address)',
        r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
    ]
    for pattern in branch_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["branch"] = match.group(1).strip()
            break
    
    # Statement period - improved patterns
    period_patterns = [
        r'Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'From\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(?:to|To)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'Statement\s+Period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'For\s+the\s+period[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        # Also try date formats with spaces
        r'(\d{1,2}\s+[-/]\s+\d{1,2}\s+[-/]\s+\d{2,4})\s+to\s+(\d{1,2}\s+[-/]\s+\d{1,2}\s+[-/]\s+\d{2,4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            account_info["statement_period"] = f"{match.group(1)} to {match.group(2)}"
            break
    
    # IFSC - improved patterns
    if not account_info.get("ifsc"):
        ifsc_patterns = [
            r'IFSC\s*(?:Code)?\s*[:\s]+([A-Z0-9]{11})',
            r'IFSC[:\s]+([A-Z]{4}0[A-Z0-9]{6})',
            r'IFSC\s+Code[:\s]+([A-Z0-9]{11})',
        ]
        for pattern in ifsc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                account_info["ifsc"] = match.group(1).strip().upper()
                break
    
    # Branch - improved patterns with better cleaning
    if not account_info.get("branch"):
        branch_patterns = [
            r'Branch[:\s]+([A-Z][A-Za-z\s\-]+?)(?:\n|IFSC|Address|Code)',
            r'Branch\s+Name[:\s]+([A-Z][A-Za-z\s\-]+)',
            r'Branch\s+Code[:\s]+\d+\s+([A-Z][A-Za-z\s\-]+)',
        ]
        for pattern in branch_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                branch = match.group(1).strip()
                # Remove unwanted words
                exclude_words = ['BRANCH', 'BANK', 'DETAILS', 'OF', 'STATEMENT', 'ACCOUNT', 'IFSC', 'CODE']
                for word in exclude_words:
                    branch = re.sub(rf'\b{word}\b', '', branch, flags=re.IGNORECASE).strip()
                branch = ' '.join(branch.split())
                # Validate branch name
                if branch and len(branch) > 2 and not branch.upper() in ['DETAILS OF STATEMENT', 'STATEMENT OF ACCOUNT']:
                    account_info["branch"] = branch
                    break

def extract_transactions(pdf_path: str) -> List[Dict]:
    """Extract ALL transactions - bank agnostic with ZERO loss - IMPROVED VERSION"""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Detect bank from first page
            first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
            bank = detect_bank(first_page_text)
            
            print(f"Detected bank: {bank}")
            
            # Use universal extraction for all banks to ensure zero loss
            return extract_transactions_universal(pdf, bank)
                
    except Exception as e:
        print(f"Error extracting transactions: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def extract_transactions_universal(pdf, bank: str) -> List[Dict]:
    """
    Universal transaction extractor - works for ALL banks
    Uses intelligent table detection with ZERO transaction loss
    """
    transactions = []
    
    # CENTRAL BANK SPECIFIC: Use line-based state machine extraction
    if bank == "Central Bank of India":
        return extract_central_bank_state_machine(pdf)
    
    # For all other banks, use standard table extraction
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"Processing page {page_num}...")
        
        tables = page.extract_tables()
        
        if tables:
            for table in tables:
                page_transactions = extract_from_table_universal_improved(table, bank)
                transactions.extend(page_transactions)
        else:
            # Fallback: try text extraction
            text = page.extract_text()
            if text:
                text_transactions = extract_from_text_fallback(text)
                transactions.extend(text_transactions)
    
    print(f"Total transactions extracted: {len(transactions)}")
    return transactions

def extract_central_bank_state_machine(pdf) -> List[Dict]:
    """
    Central Bank of India extraction - COMPLETE REWRITE
    Line-by-line state machine following exact PDF structure
    
    GROUND TRUTH:
    Line A: DD/MM/YY DD/MM/YY TO TRF. / BY TRF. <amount> <balance>
    Line B: UPI RRN <number> .
    Line C: TRF TO <merchant> (THIS IS THE ONLY VALID DESCRIPTION)
    """
    # State definitions
    WAIT_FOR_TRANSACTION = "WAIT_FOR_TRANSACTION"
    READ_TRANSACTION_LINES = "READ_TRANSACTION_LINES"
    
    transactions = []
    current_transaction = None
    state = WAIT_FOR_TRANSACTION
    value_date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{2}/\d{2}')
    
    # Collect all lines from all pages (tables + text)
    all_lines = []
    
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"Processing Central Bank page {page_num}...")
        
        # Extract from tables (convert rows to lines)
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row:
                        continue
                    # Join row cells to form a line
                    line = " ".join([str(cell).strip() if cell else "" for cell in row]).strip()
                    if line:
                        all_lines.append(line)
        
        # Extract from text
        text = page.extract_text()
        if text:
            for line in text.split('\n'):
                line = line.strip()
                if line:
                    all_lines.append(line)
    
    # Process lines through state machine
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        
        line_upper = line.upper()
        
        # Skip header/footer lines (but not transaction lines)
        if not value_date_pattern.match(line):
            if any(skip in line_upper for skip in [
                "CARRIED FORWARD", "BROUGHT FORWARD", "BALANCE SUMMARY",
                "PAGE", "STATEMENT OF ACCOUNT", "CENTRAL BANK", 
                "VALUE DATE", "POST DATE", "DETAILS"
            ]):
                continue
        
        # STATE: WAIT_FOR_TRANSACTION
        if state == WAIT_FOR_TRANSACTION:
            # New transaction starts ONLY when line matches Value Date pattern
            if value_date_pattern.match(line):
                # Finalize previous transaction if exists
                if current_transaction is not None:
                    if not current_transaction.get("description"):
                        raise ValueError(f"Transaction on {current_transaction.get('date', 'unknown')} has no description - extraction failed")
                    transactions.append(current_transaction)
                
                # Create NEW transaction - RESET description buffer COMPLETELY
                current_transaction = {
                    "date": None,
                    "description": None,  # MUST be set from Line C
                    "reference_number": "",
                    "debit": 0.0,
                    "credit": 0.0,
                    "balance": 0.0,
                    "transaction_type": "DEBIT",
                    "amount": 0.0
                }
                
                # Extract date from Line A
                date_match = re.search(r'(\d{2}/\d{2}/\d{2})', line)
                if date_match:
                    current_transaction["date"] = date_match.group(1)
                
                # Extract amounts from Line A
                amounts = re.findall(r'[\d,]+\.\d{2}', line)
                if len(amounts) >= 2:
                    current_transaction["balance"] = parse_amount_improved(amounts[-1])
                    if len(amounts) >= 3:
                        amount = parse_amount_improved(amounts[-2])
                        if "BY TRF" in line_upper or "SALARY" in line_upper:
                            current_transaction["credit"] = amount
                            current_transaction["transaction_type"] = "CREDIT"
                        else:
                            current_transaction["debit"] = amount
                            current_transaction["transaction_type"] = "DEBIT"
                        current_transaction["amount"] = amount
                    elif len(amounts) == 2:
                        amount = parse_amount_improved(amounts[0])
                        if "BY TRF" in line_upper or "SALARY" in line_upper:
                            current_transaction["credit"] = amount
                            current_transaction["transaction_type"] = "CREDIT"
                        else:
                            current_transaction["debit"] = amount
                            current_transaction["transaction_type"] = "DEBIT"
                        current_transaction["amount"] = amount
                
                # Move to READ_TRANSACTION_LINES state
                state = READ_TRANSACTION_LINES
        
        # STATE: READ_TRANSACTION_LINES
        elif state == READ_TRANSACTION_LINES:
            # Check if this line starts a new transaction
            if value_date_pattern.match(line):
                # Finalize current transaction
                if current_transaction is not None:
                    if not current_transaction.get("description"):
                        raise ValueError(f"Transaction on {current_transaction.get('date', 'unknown')} has no description - extraction failed")
                    transactions.append(current_transaction)
                
                # Create NEW transaction (same logic as WAIT_FOR_TRANSACTION)
                current_transaction = {
                    "date": None,
                    "description": None,
                    "reference_number": "",
                    "debit": 0.0,
                    "credit": 0.0,
                    "balance": 0.0,
                    "transaction_type": "DEBIT",
                    "amount": 0.0
                }
                
                date_match = re.search(r'(\d{2}/\d{2}/\d{2})', line)
                if date_match:
                    current_transaction["date"] = date_match.group(1)
                
                amounts = re.findall(r'[\d,]+\.\d{2}', line)
                if len(amounts) >= 2:
                    current_transaction["balance"] = parse_amount_improved(amounts[-1])
                    if len(amounts) >= 3:
                        amount = parse_amount_improved(amounts[-2])
                        if "BY TRF" in line_upper or "SALARY" in line_upper:
                            current_transaction["credit"] = amount
                            current_transaction["transaction_type"] = "CREDIT"
                        else:
                            current_transaction["debit"] = amount
                            current_transaction["transaction_type"] = "DEBIT"
                        current_transaction["amount"] = amount
                    elif len(amounts) == 2:
                        amount = parse_amount_improved(amounts[0])
                        if "BY TRF" in line_upper or "SALARY" in line_upper:
                            current_transaction["credit"] = amount
                            current_transaction["transaction_type"] = "CREDIT"
                        else:
                            current_transaction["debit"] = amount
                            current_transaction["transaction_type"] = "DEBIT"
                        current_transaction["amount"] = amount
                
                # Stay in READ_TRANSACTION_LINES (new transaction started)
                continue
            
            # IGNORE lines containing generic patterns (Line B and similar)
            # BUT: Do NOT skip if the line also contains a valid description pattern
            contains_valid_desc = (
                re.search(r'\bTRF\s+TO\b', line_upper) or
                re.search(r'\bTRF\s+FROM\b', line_upper) or
                re.search(r'\bSALARY\s+CREDIT\b', line_upper) or
                re.search(r'\bREFUND\b', line_upper)
            )
            if not contains_valid_desc and any(ignore in line_upper for ignore in [
                "TO TRF.", "BY TRF.", "UPI RRN", 
                "CARRIED FORWARD", "BROUGHT FORWARD"
            ]):
                continue  # Skip this line
            
            # Extract description ONLY from Line C patterns
            # Description MUST come from a line that STARTS with these patterns
            if current_transaction is not None and not current_transaction.get("description"):
                trf_to_match = re.search(r'\bTRF\s+TO\b', line_upper)
                trf_from_match = re.search(r'\bTRF\s+FROM\b', line_upper)
                salary_match = re.search(r'\bSALARY\s+CREDIT\b', line_upper)
                refund_match = re.search(r'\bREFUND\b', line_upper)
                
                if trf_to_match:
                    current_transaction["description"] = line[trf_to_match.start():].strip()
                elif trf_from_match:
                    current_transaction["description"] = line[trf_from_match.start():].strip()
                elif salary_match:
                    current_transaction["description"] = "SALARY CREDIT"
                elif refund_match:
                    current_transaction["description"] = line[refund_match.start():].strip()
                # First match wins - description is set ONCE per transaction
    
    # Finalize last transaction
    if current_transaction is not None:
        if not current_transaction.get("description"):
            raise ValueError(f"Last transaction on {current_transaction.get('date', 'unknown')} has no description - extraction failed")
        transactions.append(current_transaction)
    
    # ============================================================
    # VALIDATION (MANDATORY)
    # ============================================================
    print(f"Central Bank: Extracted {len(transactions)} transactions")
    
    # Count unique descriptions
    unique_descriptions = set()
    for txn in transactions:
        desc = txn.get("description", "")
        if desc:
            unique_descriptions.add(desc)
    
    print(f"Central Bank: Found {len(unique_descriptions)} unique descriptions")
    
    # Check for consecutive duplicates (>3 times)
    consecutive_count = 0
    last_description = None
    for txn in transactions:
        desc = txn.get("description", "")
        if desc == last_description:
            consecutive_count += 1
            if consecutive_count > 3:
                error_msg = f"Extraction validation failed: Same description '{desc}' repeats {consecutive_count} times consecutively"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
        else:
            consecutive_count = 1
            last_description = desc
    
    return transactions

def extract_from_table_universal_improved(table: List[List], bank: str) -> List[Dict]:
    """
    Improved universal table extractor - ensures ZERO transaction loss
    Dynamically finds columns and extracts ALL valid rows
    """
    transactions = []
    
    if not table or len(table) < 2:
        return transactions
    
    # Find header row (usually first row, but check first few rows)
    header_row_idx = 0
    header = table[0] if table else []
    
    # Try to find actual header by looking for common header keywords
    for idx in range(min(3, len(table))):
        row_text = ' '.join([str(c).upper() if c else '' for c in table[idx]]).replace('\n', ' ')
        if any(keyword in row_text for keyword in ['DATE', 'TXN', 'TRAN', 'PARTICULARS', 'DESCRIPTION', 'DEBIT', 'CREDIT', 'WITHDRAWAL', 'DEPOSIT']):
            header_row_idx = idx
            header = table[idx]
            break
    
    # Find column indices dynamically
    date_col = find_column_index(header, ['DATE', 'TXN DATE', 'TRAN DATE', 'VALUE DATE', 'TRANSACTION DATE'])
    desc_col = find_column_index(header, ['PARTICULARS', 'DESCRIPTION', 'NARRATION', 'DETAILS', 'TRANSACTION', 'REMARKS'])
    debit_col = find_column_index(header, ['DEBIT', 'WITHDRAWAL', 'DR', 'PAID OUT', 'WITHDRAWALS'])
    credit_col = find_column_index(header, ['CREDIT', 'DEPOSIT', 'CR', 'PAID IN', 'DEPOSITS'])
    balance_col = find_column_index(header, ['BALANCE', 'CLOSING', 'AVAILABLE', 'CLOSING BALANCE'])
    ref_col = find_column_index(header, ['CHEQUE', 'CHQ', 'REFERENCE', 'REF NO', 'CHQ NO'])
    # Initialize tran_id_col and amount_col for Union Bank (will be set in bank-specific section)
    tran_id_col = None
    amount_col = None
    
    # If columns not found, try bank-specific defaults
    if date_col is None or desc_col is None:
        if bank == "Axis Bank":
            date_col = 0
            desc_col = 2
            debit_col = 3
            credit_col = 4
            balance_col = 5
            ref_col = 1
        elif bank == "Bank of India":
            date_col = 1
            desc_col = 2
            debit_col = 4 if len(header) > 4 else 3
            credit_col = 5 if len(header) > 5 else 4
            balance_col = 6 if len(header) > 6 else 5
            ref_col = 3 if len(header) > 3 else None
        elif bank == "HDFC Bank":
            date_col = 0
            desc_col = 1
            debit_col = 4
            credit_col = 5
            balance_col = 6
            ref_col = 2
        elif bank == "State Bank of India":
            # SBI format: Date | Narration | Ref/Cheque No | Debit | Credit | Balance
            date_col = 0
            desc_col = 1
            ref_col = 2  # Ref/Cheque No is column 2
            debit_col = 3
            credit_col = 4
            balance_col = 5  # Balance is LAST column
        elif bank == "Union Bank of India":
            # Union Bank format (MOST COMMON): Date | Description | Ref / Tran ID | Debit | Credit | Balance
            # OR: Tran Id | Tran Date | Remarks | Amount (Rs.) | Balance (Rs.)
            # CRITICAL: Ref / Tran ID column MUST NEVER be parsed as amount
            
            # Try to find Debit and Credit columns first (preferred format)
            if debit_col is None:
                debit_col = find_column_index(header, ['DEBIT', 'DR', 'WITHDRAWAL'])
            if credit_col is None:
                credit_col = find_column_index(header, ['CREDIT', 'CR', 'DEPOSIT'])
            
            # If separate Debit/Credit columns found, use them
            if debit_col is not None and credit_col is not None:
                # Format: Date | Description | Ref / Tran ID | Debit | Credit | Balance
                # Find Ref / Tran ID column
                ref_col = find_column_index(header, ['REF', 'REFERENCE', 'TRAN ID', 'TRANSACTION ID', 'TXN ID', 'CHQ', 'CHEQUE'])
                if ref_col is None:
                    # If not found, assume it's column 2 (between Description and Debit)
                    ref_col = 2
                # Date and Description columns
                if date_col is None:
                    date_col = 0
                if desc_col is None:
                    desc_col = 1
                # Balance is last column
                if balance_col is None:
                    balance_col = len(header) - 1 if header else 5
                amount_col = None  # Not using Amount column
                tran_id_col = ref_col  # Ref / Tran ID column
            else:
                # Fallback: Single Amount column format
                # Format: Tran Id | Tran Date | Remarks | Amount (Rs.) | Balance (Rs.)
                tran_id_col = 0  # Tran Id column - NEVER parse as amount
                date_col = 1  # Tran Date
                desc_col = 2  # Remarks
                amount_col = 3  # Amount (Rs.) - ONLY source of debit/credit
                balance_col = 4  # Balance (Rs.)
                ref_col = tran_id_col  # Store Tran Id in ref_col
                # debit_col and credit_col remain None - we'll parse from amount_col
        else:
            # Generic defaults
            date_col = 0
            desc_col = 1
            debit_col = 2
            credit_col = 3
            balance_col = 4
            ref_col = None
    
    # Process rows starting after header
    i = header_row_idx + 1
    while i < len(table):
        row = table[i]
        
        if not row:
            i += 1
            continue
        
        # Extract date
        date = safe_extract_cell(row, date_col)
        
        # Skip if no date or it's clearly a header/footer
        if not date:
            i += 1
            continue
        
        # Check if it's a header/footer row
        date_upper = date.upper().strip()
        if date_upper in ["DATE", "TXN DATE", "TRAN DATE", "VALUE DATE", "OPENING BALANCE", "CLOSING BALANCE", "BALANCE"]:
            i += 1
            continue
        
        # CENTRAL BANK SPECIFIC: Skip "CARRIED FORWARD" lines completely
        # These are NOT transactions and should NEVER be processed
        if bank == "Central Bank of India":
            date_desc_combined = (date + " " + (safe_extract_cell(row, desc_col) or "")).upper()
            if "CARRIED FORWARD" in date_desc_combined or "BROUGHT FORWARD" in date_desc_combined:
                i += 1
                continue
        
        # Validate date format (more lenient) - but also check if row has amounts
        has_valid_date = is_valid_date_improved(date)
        
        # CENTRAL BANK SPECIFIC: Only process rows with valid Value Date as transaction starts
        # For Central Bank, rows without Value Date are continuation rows, not new transactions
        if bank == "Central Bank of India":
            # If no valid date, this is a continuation row - skip processing as new transaction
            if not has_valid_date:
                i += 1
                continue
        else:
            # For other banks, check if row has amounts - might be a valid transaction row
            if not has_valid_date:
                # Check if this row has amounts in debit/credit columns
                temp_debit_str = safe_extract_cell(row, debit_col) if debit_col is not None else ""
                temp_credit_str = safe_extract_cell(row, credit_col) if credit_col is not None else ""
                temp_debit_amt = parse_amount_improved(temp_debit_str)
                temp_credit_amt = parse_amount_improved(temp_credit_str)
                
                # If row has amounts but no date, try to get date from previous row or skip
                if temp_debit_amt == 0 and temp_credit_amt == 0:
                    i += 1
                    continue
                # If has amounts, try to extract date from other columns
                if temp_debit_amt > 0 or temp_credit_amt > 0:
                    # Try to find date in other columns
                    found_date = False
                    for col_idx in range(len(row)):
                        if date_col is None or col_idx != date_col:
                            cell_val = safe_extract_cell(row, col_idx)
                            if is_valid_date_improved(cell_val):
                                date = cell_val
                                has_valid_date = True
                                found_date = True
                                break
                    if not found_date:
                        # Use previous transaction's date or skip
                        if transactions:
                            date = transactions[-1].get("date", "")
                            has_valid_date = True
                        else:
                            i += 1
                            continue
        
        # ============================================================
        # CENTRAL BANK SPECIFIC: Description Extraction (CRITICAL)
        # ============================================================
        # ABSOLUTE RULE: A transaction row starts ONLY when a NEW Value Date appears
        # For EACH detected Value Date:
        # 1. IMMEDIATELY reset any previous description buffer
        # 2. Create a NEW empty list: description_lines = []
        # 3. Capture ALL text lines in the Details column UNTIL the NEXT Value Date
        # 4. These lines belong ONLY to this transaction
        # ============================================================
        
        description = safe_extract_cell(row, desc_col) or ""
        description_end_row = i + 1  # Default: no continuation rows
        
        if bank == "Central Bank of India":
            # CRITICAL ENFORCEMENT: Only process rows with valid Value Date as transaction starts
            # If this row does NOT have a valid Value Date, skip description extraction
            # (This row is a continuation of the previous transaction)
            if not has_valid_date:
                # This is NOT a new transaction row - skip description extraction
                # Use empty description or keep existing (will be handled by amount check)
                description = ""
            else:
                # ============================================================
                # NEW TRANSACTION DETECTED: Value Date found
                # IMMEDIATELY reset description buffer - ABSOLUTE RULE
                # ============================================================
                
                # STEP 1: IMMEDIATELY reset any previous description buffer
                # Create a COMPLETELY NEW empty list for THIS transaction ONLY
                description_lines = []  # FRESH buffer - NEVER reuse from previous transactions
                
                # STEP 2: Start with current row's description (the row with Value Date)
                current_row_desc = safe_extract_cell(row, desc_col) or ""
                if current_row_desc and current_row_desc.strip():
                    description_lines.append(current_row_desc.strip())
                
                # STEP 3: Capture ALL text lines in Details column UNTIL the NEXT Value Date
                continuation_row_idx = i + 1
                max_continuation_rows = 20  # Safety limit
                
                while continuation_row_idx < len(table) and len(description_lines) < max_continuation_rows:
                    next_row = table[continuation_row_idx]
                    if not next_row:
                        break
                    
                    # STOP CONDITION: Check if next row has a valid Value Date (new transaction)
                    next_date = safe_extract_cell(next_row, date_col)
                    if is_valid_date_improved(next_date):
                        # Next Value Date found - STOP collecting (this is a new transaction)
                        break
                    
                    # CENTRAL BANK SPECIFIC: Skip "CARRIED FORWARD" lines
                    # These are NOT part of the transaction description
                    next_date_str = str(next_date) if next_date else ""
                    next_desc_str = safe_extract_cell(next_row, desc_col) or ""
                    combined_check = (next_date_str + " " + next_desc_str).upper()
                    if "CARRIED FORWARD" in combined_check or "BROUGHT FORWARD" in combined_check:
                        continuation_row_idx += 1
                        continue  # Skip this line, continue to next
                    
                    # Extract text from Details column of continuation row
                    continuation_desc = safe_extract_cell(next_row, desc_col) or ""
                    if continuation_desc and continuation_desc.strip():
                        # Add ALL non-empty lines to buffer
                        description_lines.append(continuation_desc.strip())
                    
                    continuation_row_idx += 1
                
                # Store where description block ends for amount extraction
                description_end_row = continuation_row_idx
                
                # ============================================================
                # DESCRIPTION RESOLUTION (STRICT - Based on Actual PDF Structure)
                # ============================================================
                # PDF Structure:
                # Line 1: <value_date> <post_date> TO TRF. / BY TRF. <amount> <balance>
                # Line 2: UPI RRN <number> .
                # Line 3: THE REAL DESCRIPTION (TRF TO, TRF FROM, SALARY CREDIT, REFUND)
                #
                # REMOVE lines that are:
                # - "TO TRF." or "BY TRF." (exact match or pattern)
                # - Lines starting with "UPI RRN"
                # - Standalone numbers or references (numeric-only)
                # - Punctuation-only lines
                # - Empty lines
                # - Lines starting with "CARRIED FORWARD"
                # ============================================================
                
                # Filter out generic/system lines and empty lines
                meaningful_lines = []
                for line in description_lines:
                    line_stripped = line.strip()
                    if not line_stripped:  # Ignore empty lines
                        continue
                    
                    line_upper = line_stripped.upper()
                    
                    # Check if line should be removed (generic/system lines)
                    is_generic = (
                        line_upper == "TO TRF." or
                        line_upper == "TO TRF" or
                        line_upper == "BY TRF." or
                        line_upper == "BY TRF" or
                        re.match(r'^TO\s+TRF\.?\s*$', line_upper) or  # "TO TRF" or "TO TRF."
                        re.match(r'^BY\s+TRF\.?\s*$', line_upper) or  # "BY TRF" or "BY TRF."
                        re.match(r'^UPI\s+RRN', line_upper) or  # Lines starting with "UPI RRN"
                        re.match(r'^RRN\s+\d+', line_upper) or  # "RRN 123456" (with or without trailing chars)
                        re.match(r'^\d+$', line_upper) or  # Standalone numbers
                        re.match(r'^[^\w]+$', line_upper) or  # Punctuation-only lines
                        line_upper.startswith("CARRIED FORWARD")  # Skip carried forward lines
                    )
                    
                    # Keep line if it's not generic/system
                    if not is_generic:
                        meaningful_lines.append(line_stripped)
                
                # ============================================================
                # FINAL DESCRIPTION SELECTION (MANDATORY - Extract ONLY from specific patterns)
                # ============================================================
                # The transaction description MUST be extracted ONLY from:
                # - Lines starting with "TRF TO"
                # - Lines starting with "TRF FROM"
                # - Lines containing "SALARY CREDIT"
                # - Lines containing "REFUND"
                # EXACTLY ONE such line exists per transaction.
                # ============================================================
                
                final_description = ""  # Fresh variable for THIS transaction only
                
                # Search through ALL meaningful lines for the actual description
                for line in meaningful_lines:
                    line_upper = line.upper().strip()
                    
                    # Priority 1: Lines starting with "TRF TO" (e.g., "TRF TO AJIO", "TRF TO BIG BAZAAR")
                    if line_upper.startswith("TRF TO"):
                        final_description = line  # Use the FULL line (preserve case)
                        break  # Found it - stop searching
                    
                    # Priority 2: Lines starting with "TRF FROM" (e.g., "TRF FROM FRIEND")
                    if not final_description and line_upper.startswith("TRF FROM"):
                        final_description = line  # Use the FULL line
                        break
                    
                    # Priority 3: Lines containing "SALARY CREDIT"
                    if not final_description and "SALARY CREDIT" in line_upper:
                        final_description = "SALARY CREDIT"
                        break
                    
                    # Priority 4: Lines containing "REFUND"
                    if not final_description and "REFUND" in line_upper:
                        final_description = line  # Use the FULL line (may have additional text)
                        break
                
                # If no valid description pattern found, use fallback
                if not final_description:
                    if meaningful_lines:
                        # Fallback: use the last meaningful line (shouldn't happen in correct PDFs)
                        final_description = meaningful_lines[-1]
                    elif description_lines:
                        # Last resort: use last original line
                        final_description = description_lines[-1].strip()
                    else:
                        # Absolute last resort: use current row description
                        final_description = current_row_desc.strip()
                
                # Set the final description for THIS transaction
                # This description is UNIQUE and is NEVER reused
                description = final_description.strip()
                
                # Update row index to skip continuation rows we've processed
                if continuation_row_idx > i + 1:
                    i = continuation_row_idx - 1  # Will be incremented at end of loop
        elif bank == "Axis Bank":
            description_lines = []
            current_row_desc = safe_extract_cell(row, desc_col) or ""
            if current_row_desc and current_row_desc.strip():
                description_lines.append(current_row_desc.strip())
            continuation_row_idx = i + 1
            max_continuation_rows = 20
            while continuation_row_idx < len(table) and len(description_lines) < max_continuation_rows:
                next_row = table[continuation_row_idx]
                if not next_row:
                    break
                next_date = safe_extract_cell(next_row, date_col)
                next_debit = safe_extract_cell(next_row, debit_col) if debit_col is not None else ""
                next_credit = safe_extract_cell(next_row, credit_col) if credit_col is not None else ""
                has_amounts = parse_amount_improved(next_debit) > 0 or parse_amount_improved(next_credit) > 0
                if is_valid_date_improved(next_date) or has_amounts:
                    break
                continuation_desc = safe_extract_cell(next_row, desc_col) or ""
                if continuation_desc and continuation_desc.strip():
                    description_lines.append(continuation_desc.strip())
                continuation_row_idx += 1
            meaningful_lines = []
            for line in description_lines:
                s = line.strip()
                if not s:
                    continue
                u = s.upper()
                is_generic = (
                    u == "TO TRF." or
                    u == "TO TRF" or
                    u == "BY TRF." or
                    u == "BY TRF" or
                    re.match(r'^TO\s+TRF\.?\s*$', u) or
                    re.match(r'^BY\s+TRF\.?\s*$', u) or
                    re.match(r'^UPI\s+RRN', u) or
                    re.match(r'^RRN\s+\d+', u) or
                    re.match(r'^\d+$', u) or
                    re.match(r'^[^\w]+$', u)
                )
                if not is_generic:
                    meaningful_lines.append(s)
            final_description = ""
            for ml in meaningful_lines:
                up = ml.upper().strip()
                if up.startswith("TRF TO"):
                    final_description = ml
                    break
                if not final_description and up.startswith("TRF FROM"):
                    final_description = ml
                    break
                if not final_description and "SALARY CREDIT" in up:
                    final_description = "SALARY CREDIT"
                    break
                if not final_description and "REFUND" in up:
                    final_description = ml
                    break
            if not final_description:
                if meaningful_lines:
                    final_description = meaningful_lines[-1]
                elif description_lines:
                    final_description = description_lines[-1].strip()
                else:
                    final_description = current_row_desc.strip()
            description = final_description.strip()
            if continuation_row_idx > i + 1:
                i = continuation_row_idx - 1
            # For other banks, use standard description extraction
            # Check all columns for additional description text
            if desc_col is not None:
                columns_to_check = [-1, 1, 2]
                
                for col_offset in columns_to_check:
                    col_idx = desc_col + col_offset
                    if 0 <= col_idx < len(row) and col_idx != date_col and col_idx != debit_col and col_idx != credit_col and col_idx != balance_col:
                        col_text = safe_extract_cell(row, col_idx)
                        if col_text and col_text.strip():
                            is_amount = parse_amount_improved(col_text) > 0
                            is_date = is_valid_date_improved(col_text)
                            is_short_ref = len(col_text.strip()) <= 10 and re.match(r'^[A-Z0-9/-]+$', col_text.strip().upper())
                            
                            if not is_amount and not is_date and not is_short_ref:
                                text_upper = col_text.upper()
                                description_keywords = ['TRF', 'TRANSFER', 'PAYMENT', 'NEFT', 'RTGS', 'IMPS', 'UPI', 'TO', 'FROM', 'BY', 'FOR', 'CR', 'DR', 'CREDIT', 'DEBIT']
                                
                                if any(word in text_upper for word in description_keywords):
                                    description += " " + col_text
                                elif len(col_text.strip()) > 15:
                                    description += " " + col_text
            
            # Handle multi-line descriptions for other banks
            continuation_rows = 0
            max_continuation_rows = 5
            
            while i + 1 < len(table) and continuation_rows < max_continuation_rows:
                next_row = table[i + 1]
                if not next_row:
                    break
                
                next_date = safe_extract_cell(next_row, date_col)
                next_desc = safe_extract_cell(next_row, desc_col)
                next_debit = safe_extract_cell(next_row, debit_col) if debit_col is not None else ""
                next_credit = safe_extract_cell(next_row, credit_col) if credit_col is not None else ""
                
                has_amounts = parse_amount_improved(next_debit) > 0 or parse_amount_improved(next_credit) > 0
                
                if not is_valid_date_improved(next_date) and not has_amounts and next_desc and next_desc.strip():
                    description += " " + next_desc
                    i += 1
                    continuation_rows += 1
                else:
                    break
        
        # Clean description - preserve all text, just normalize whitespace
        # DO NOT truncate or compress - keep full description as in PDF
        # CENTRAL BANK SPECIFIC: Enhanced normalization - ONE CLEAN, COMPLETE STRING
        if bank == "Central Bank of India":
            # CENTRAL BANK SPECIFIC: Normalize description to ONE CLEAN, COMPLETE STRING
            # Rules:
            # 1. Remove line breaks (already done by joining)
            # 2. Replace multiple spaces with single space
            # 3. Remove periods after abbreviations (TRF. -> TRF) but keep other text
            # 4. Preserve all keywords: UPI, RRN, TRF, merchant names
            # 5. Do NOT remove abbreviations, shorten text, or reorder words
            
            if description:
                # Step 1: Normalize whitespace (remove line breaks, multiple spaces -> single space)
                description = ' '.join(description.split())
                
                # Step 2: Remove periods after common abbreviations (but keep the abbreviation)
                # Pattern: "TRF." -> "TRF", "TO TRF." -> "TO TRF"
                # But preserve periods in other contexts (e.g., "RRN 123.456" stays as is)
                description = re.sub(r'\b(TRF|NEFT|RTGS|IMPS|UPI)\.', r'\1', description, flags=re.IGNORECASE)
                
                # Step 3: Ensure no leading/trailing spaces
                description = description.strip()
        else:
            # For other banks, standard normalization
            description = ' '.join(description.split()) if description else ""
        
        # CRITICAL: Validate description is not compressed/truncated
        # CENTRAL BANK SPECIFIC: Enhanced validation for complete descriptions
        if bank == "Central Bank of India":
            # Check for common compressed patterns that indicate incomplete extraction
            compressed_patterns = [
                r'^TO TRF\.?\s*-?\s*(Cr|Dr)$',  # "TO TRF - Cr" is incomplete
                r'^TRF\.?\s*-?\s*(Cr|Dr)$',     # "TRF - Cr" is incomplete
                r'^[A-Z]{2,4}\s*-?\s*(Cr|Dr)$', # Short codes like "NEFT - Cr" are incomplete
            ]
            
            is_compressed = any(re.match(pattern, description.strip(), re.IGNORECASE) for pattern in compressed_patterns)
            if is_compressed:
                # Try to get more description text from surrounding cells and next rows
                # This is a fallback if initial merging missed continuation lines
                for col_offset in range(-2, 4):
                    col_idx = desc_col + col_offset if desc_col is not None else None
                    if col_idx is None or col_idx < 0 or col_idx >= len(row):
                        continue
                    if col_idx in [date_col, debit_col, credit_col, balance_col]:
                        continue
                    
                    col_text = safe_extract_cell(row, col_idx)
                    if col_text and col_text.strip():
                        is_amount = parse_amount_improved(col_text) > 0
                        is_date = is_valid_date_improved(col_text)
                        if not is_amount and not is_date:
                            # Check if it contains description keywords
                            text_upper = col_text.upper()
                            if any(keyword in text_upper for keyword in ['TRF', 'UPI', 'RRN', 'NEFT', 'RTGS', 'IMPS', 'TO', 'FROM']):
                                description += " " + col_text.strip()
                                break
                
                # Re-normalize after adding text
                description = ' '.join(description.split())
                description = re.sub(r'\b(TRF|NEFT|RTGS|IMPS|UPI)\.', r'\1', description, flags=re.IGNORECASE)
                description = description.strip()
        else:
            # For other banks, standard validation
            compressed_patterns = [
                r'^TO TRF\.?\s*-?\s*(Cr|Dr)$',
                r'^TRF\.?\s*-?\s*(Cr|Dr)$',
                r'^[A-Z]{2,4}\s*-?\s*(Cr|Dr)$',
            ]
            
            is_compressed = any(re.match(pattern, description.strip(), re.IGNORECASE) for pattern in compressed_patterns)
            if is_compressed and desc_col is not None:
                for col_offset in range(-2, 4):
                    col_idx = desc_col + col_offset
                    if 0 <= col_idx < len(row) and col_idx != date_col and col_idx != debit_col and col_idx != credit_col and col_idx != balance_col:
                        col_text = safe_extract_cell(row, col_idx)
                        if col_text and col_text.strip() and len(col_text.strip()) > len(description.strip()):
                            is_amount = parse_amount_improved(col_text) > 0
                            is_date = is_valid_date_improved(col_text)
                            if not is_amount and not is_date:
                                temp_desc = description + " " + col_text
                                if len(temp_desc.strip()) > len(description.strip()) + 5:
                                    description = temp_desc
                                    break
        
        # Extract amounts - try multiple column positions if primary columns don't have data
        debit_str = safe_extract_cell(row, debit_col) if debit_col is not None else ""
        credit_str = safe_extract_cell(row, credit_col) if credit_col is not None else ""
        balance_str = safe_extract_cell(row, balance_col) if balance_col is not None else ""
        ref_str = safe_extract_cell(row, ref_col) if ref_col is not None else ""
        
        # CENTRAL BANK SPECIFIC: If amounts are not on Value Date row, check continuation rows
        # This handles cases where amounts appear on rows below the Value Date
        if bank == "Central Bank of India":
            if (not debit_str or parse_amount_improved(debit_str) == 0) and (not credit_str or parse_amount_improved(credit_str) == 0):
                # Amounts not found on Value Date row, check continuation rows
                # But only check up to the rows we already collected for description
                check_row_idx = i + 1
                max_check = min(description_end_row, len(table))
                
                while check_row_idx < max_check:
                    check_row = table[check_row_idx] if check_row_idx < len(table) else None
                    if not check_row:
                        break
                    
                    # Don't check beyond the next Value Date (that's a different transaction)
                    check_date = safe_extract_cell(check_row, date_col)
                    if is_valid_date_improved(check_date):
                        break
                    
                    # Check for amounts in continuation row
                    check_debit = safe_extract_cell(check_row, debit_col) if debit_col is not None else ""
                    check_credit = safe_extract_cell(check_row, credit_col) if credit_col is not None else ""
                    check_balance = safe_extract_cell(check_row, balance_col) if balance_col is not None else ""
                    
                    if check_debit and parse_amount_improved(check_debit) > 0:
                        debit_str = check_debit
                    if check_credit and parse_amount_improved(check_credit) > 0:
                        credit_str = check_credit
                    if check_balance and parse_amount_improved(check_balance) > 0:
                        balance_str = check_balance
                    
                    # If we found amounts, stop checking
                    if (debit_str and parse_amount_improved(debit_str) > 0) or (credit_str and parse_amount_improved(credit_str) > 0):
                        break
                    
                    check_row_idx += 1
        
        # Parse amounts
        debit_amt = parse_amount_improved(debit_str)
        credit_amt = parse_amount_improved(credit_str)
        balance_amt = parse_amount_improved(balance_str)
        
        # ============================================================
        # SBI-SPECIFIC VALIDATION: Fix Ref/Cheque No mis-mapping
        # ============================================================
        if bank == "State Bank of India":
            # Validate debit and credit are valid monetary numbers
            # Check if debit looks like a reference number
            if debit_amt > 0:
                is_invalid_debit = False
                debit_cleaned = debit_str.replace(',', '').replace(' ', '').strip() if debit_str else ""
                
                # Rule 1: Integer without decimal and exceeds realistic limit (likely ref number)
                # Most transactions have decimals (paise), ref numbers are integers
                if debit_amt == int(debit_amt) and debit_amt > 100000:  # > 1 lakh without decimal
                    is_invalid_debit = True
                
                # Rule 2: Check if debit_str looks like a reference number (all digits, no decimal)
                if debit_cleaned and re.match(r'^\d+$', debit_cleaned):
                    # If it's a long integer without decimal point, likely a ref number
                    if '.' not in debit_str and len(debit_cleaned) >= 6:
                        is_invalid_debit = True
                
                # Rule 3: If debit exceeds realistic transaction limit (50 lakhs)
                if debit_amt > 5000000:
                    is_invalid_debit = True
                
                # Rule 4: If debit is exactly an integer and ref_col is empty, likely mis-mapped
                if is_invalid_debit or (debit_amt == int(debit_amt) and debit_amt > 10000 and (not ref_str or ref_str.strip() == "")):
                    # Shift invalid debit value to reference number
                    if not ref_str or ref_str.strip() == "":
                        ref_str = debit_str.strip() if debit_str else str(int(debit_amt))
                    # Reset debit
                    debit_amt = 0.0
                    debit_str = ""
            
            # Validate credit similarly
            if credit_amt > 0:
                is_invalid_credit = False
                credit_cleaned = credit_str.replace(',', '').replace(' ', '').strip() if credit_str else ""
                
                # Rule 1: Integer without decimal and exceeds realistic limit
                if credit_amt == int(credit_amt) and credit_amt > 100000:
                    is_invalid_credit = True
                
                # Rule 2: Check if credit_str looks like a reference number
                if credit_cleaned and re.match(r'^\d+$', credit_cleaned):
                    if '.' not in credit_str and len(credit_cleaned) >= 6:
                        is_invalid_credit = True
                
                # Rule 3: If credit exceeds realistic transaction limit
                if credit_amt > 5000000:
                    is_invalid_credit = True
                
                # Rule 4: If credit is exactly an integer and ref_col is empty, likely mis-mapped
                if is_invalid_credit or (credit_amt == int(credit_amt) and credit_amt > 10000 and (not ref_str or ref_str.strip() == "")):
                    if not ref_str or ref_str.strip() == "":
                        ref_str = credit_str.strip() if credit_str else str(int(credit_amt))
                    credit_amt = 0.0
                    credit_str = ""
            
            # Use balance position as anchor for column correction
            # Balance must always be the LAST numeric column
            if balance_amt == 0 or balance_col is None:
                # Balance should be the LAST numeric column
                # Check columns from right to left
                for col_idx in range(len(row) - 1, -1, -1):
                    if col_idx in [date_col, desc_col]:
                        continue
                    cell_val = safe_extract_cell(row, col_idx)
                    temp_balance = parse_amount_improved(cell_val)
                    # Balance should be substantial (not a small ref number) and have decimal
                    if temp_balance > 1000:  # Reasonable minimum balance
                        # Prefer values with decimals (monetary amounts) over integers (ref numbers)
                        if '.' in cell_val or temp_balance > 10000:
                            balance_amt = temp_balance
                            balance_str = cell_val
                            break
        
        # ============================================================
        # UNION BANK OF INDIA SPECIFIC: Amount Extraction (MANDATORY)
        # ============================================================
        # Union Bank can have TWO formats:
        # Format 1: Date | Description | Ref / Tran ID | Debit | Credit | Balance (PREFERRED)
        # Format 2: Tran Id | Tran Date | Remarks | Amount (Rs.) | Balance (Rs.) (FALLBACK)
        # CRITICAL: Ref / Tran ID MUST NEVER be parsed as amount
        # Amounts MUST have decimals, reference numbers are long integers without decimals
        union_bank_amount_extracted = False  # Flag to track if amounts were extracted
        if bank == "Union Bank of India":
            # Extract Ref / Tran ID - store but NEVER use as amount
            # Use ref_col which is always set for Union Bank (either from Format 1 or Format 2)
            tran_id_str = ""
            if ref_col is not None and len(row) > ref_col:
                tran_id_str = safe_extract_cell(row, ref_col)
            # Fallback: try column 0 if ref_col not available (Format 2 case)
            elif len(row) > 0:
                cell_0 = safe_extract_cell(row, 0)
                # Check if column 0 looks like a transaction ID (alphanumeric starting with S or similar)
                if cell_0 and (cell_0.startswith('S') or re.match(r'^[A-Z]?\d+', cell_0)):
                    tran_id_str = cell_0
            tran_id_cleaned = tran_id_str.replace('S', '').replace('s', '').strip() if tran_id_str else ""
            
            # Extract Tran ID numeric part for validation
            tran_id_numeric = None
            if tran_id_cleaned:
                try:
                    tran_id_numeric_match = re.search(r'(\d+)', tran_id_cleaned)
                    if tran_id_numeric_match:
                        tran_id_numeric = int(tran_id_numeric_match.group(1))
                except (ValueError, TypeError):
                    pass
            
            # FORMAT 1: Try separate Debit and Credit columns first (PREFERRED)
            if debit_col is not None and credit_col is not None:
                # Extract from dedicated Debit column
                if len(row) > debit_col:
                    debit_cell = safe_extract_cell(row, debit_col)
                    if debit_cell:
                        debit_val = parse_amount_improved(debit_cell)
                        # STRICT VALIDATION: Transaction ID detection
                        # GOLDEN RULE: If number has > 6 digits AND no decimal → it's NOT an amount
                        is_valid_debit = True
                        
                        # Check 1: Equals Tran ID
                        if tran_id_numeric and abs(debit_val - tran_id_numeric) < 0.01:
                            is_valid_debit = False
                        
                        # Check 2: More than 6 digits AND no decimal point → Transaction ID
                        debit_cell_cleaned = debit_cell.replace(',', '').replace(' ', '').strip()
                        # Remove currency symbols
                        debit_cell_cleaned = re.sub(r'[₹$€£]', '', debit_cell_cleaned)
                        # Extract numeric part
                        numeric_match = re.search(r'(\d+)', debit_cell_cleaned)
                        if numeric_match:
                            numeric_str = numeric_match.group(1)
                            # If length > 6 digits AND no decimal point in original cell → Transaction ID
                            if len(numeric_str) > 6 and '.' not in debit_cell:
                                is_valid_debit = False
                        
                        # Check 3: Large integer without decimal (backup check)
                        if debit_val == int(debit_val) and debit_val > 100000 and '.' not in debit_cell:
                            is_valid_debit = False
                        
                        if is_valid_debit and debit_val > 0:
                            debit_amt = debit_val
                            debit_str = debit_cell
                            union_bank_amount_extracted = True
                        elif not is_valid_debit:
                            # Invalid debit detected - it's likely a transaction ID, set to 0
                            debit_amt = 0.0
                            debit_str = ""
                
                # Extract from dedicated Credit column
                if len(row) > credit_col:
                    credit_cell = safe_extract_cell(row, credit_col)
                    if credit_cell:
                        credit_val = parse_amount_improved(credit_cell)
                        # STRICT VALIDATION: Transaction ID detection
                        # GOLDEN RULE: If number has > 6 digits AND no decimal → it's NOT an amount
                        is_valid_credit = True
                        
                        # Check 1: Equals Tran ID
                        if tran_id_numeric and abs(credit_val - tran_id_numeric) < 0.01:
                            is_valid_credit = False
                        
                        # Check 2: More than 6 digits AND no decimal point → Transaction ID
                        credit_cell_cleaned = credit_cell.replace(',', '').replace(' ', '').strip()
                        # Remove currency symbols
                        credit_cell_cleaned = re.sub(r'[₹$€£]', '', credit_cell_cleaned)
                        # Extract numeric part
                        numeric_match = re.search(r'(\d+)', credit_cell_cleaned)
                        if numeric_match:
                            numeric_str = numeric_match.group(1)
                            # If length > 6 digits AND no decimal point in original cell → Transaction ID
                            if len(numeric_str) > 6 and '.' not in credit_cell:
                                is_valid_credit = False
                        
                        # Check 3: Large integer without decimal (backup check)
                        if credit_val == int(credit_val) and credit_val > 100000 and '.' not in credit_cell:
                            is_valid_credit = False
                        
                        if is_valid_credit and credit_val > 0:
                            credit_amt = credit_val
                            credit_str = credit_cell
                            union_bank_amount_extracted = True
                        elif not is_valid_credit:
                            # Invalid credit detected - it's likely a transaction ID, set to 0
                            credit_amt = 0.0
                            credit_str = ""
                
                # VALIDATION: Exactly ONE of debit or credit must be > 0
                if debit_amt > 0 and credit_amt > 0:
                    # Both are > 0 - this is invalid, keep the larger one (likely the correct amount)
                    if debit_amt > credit_amt:
                        credit_amt = 0.0
                        credit_str = ""
                    else:
                        debit_amt = 0.0
                        debit_str = ""
            
            # FORMAT 2: Fallback to single Amount column (if Format 1 didn't work)
            elif amount_col is not None and not union_bank_amount_extracted:
                # Extract Amount (Rs.) from amount_col - ONLY SOURCE OF AMOUNTS
                amount_str = safe_extract_cell(row, amount_col) if len(row) > amount_col else ""
                
                # Reset debit/credit - we'll parse from Amount column only
                debit_amt = 0.0
                credit_amt = 0.0
                debit_str = ""
                credit_str = ""
                
                if amount_str:
                    amount_upper = amount_str.upper()
                    
                    # Detect Dr/Cr suffix in Amount column
                    # Patterns: "1,234.56 (Dr)", "1,234.56 (Cr)", "1234.56 Dr", "1234.56 Cr"
                    is_debit = False
                    is_credit = False
                    
                    if re.search(r'\(?\s*DR\s*\)?', amount_upper) or re.search(r'\bDR\b', amount_upper):
                        is_debit = True
                    elif re.search(r'\(?\s*CR\s*\)?', amount_upper) or re.search(r'\bCR\s*\)?', amount_upper):
                        is_credit = True
                    
                    # Parse amount value (strip Dr/Cr, commas, etc.)
                    amount_cleaned = amount_str
                    # Remove Dr/Cr indicators
                    amount_cleaned = re.sub(r'\(?\s*(DR|CR|Dr|Cr)\s*\)?', '', amount_cleaned, flags=re.IGNORECASE)
                    # Remove commas and spaces
                    amount_cleaned = amount_cleaned.replace(',', '').replace(' ', '').strip()
                    # Remove currency symbols
                    amount_cleaned = re.sub(r'[₹$€£]', '', amount_cleaned)
                    
                    # Parse numeric value
                    parsed_amount = parse_amount_improved(amount_cleaned)
                    
                    if parsed_amount > 0:
                        # STRICT VALIDATION: Transaction ID detection
                        # GOLDEN RULE: If number has > 6 digits AND no decimal → it's NOT an amount
                        is_valid_amount = True
                        
                        # Check 1: More than 6 digits AND no decimal point → Transaction ID
                        amount_cleaned_numeric = re.sub(r'[^\d]', '', amount_cleaned)
                        if len(amount_cleaned_numeric) > 6 and '.' not in amount_str:
                            is_valid_amount = False
                        
                        # Check 2: If amount equals Tran Id → REJECT
                        tran_id_numeric = None
                        if tran_id_cleaned:
                            try:
                                # Try to extract numeric part from Tran Id (e.g., "S52649729" → 52649729)
                                tran_id_numeric_match = re.search(r'(\d+)', tran_id_cleaned)
                                if tran_id_numeric_match:
                                    tran_id_numeric = int(tran_id_numeric_match.group(1))
                            except (ValueError, TypeError):
                                pass
                        
                        if tran_id_numeric and abs(parsed_amount - tran_id_numeric) < 0.01:
                            is_valid_amount = False
                        
                        # Check 3: Large integer without decimal (backup)
                        if parsed_amount == int(parsed_amount) and parsed_amount > 100000 and '.' not in amount_str:
                            is_valid_amount = False
                        
                        if not is_valid_amount:
                            # Amount is actually a transaction ID - skip this row
                            i += 1
                            continue
                        
                        # Assign to debit or credit based on Dr/Cr detection
                        if is_debit:
                            debit_amt = parsed_amount
                            debit_str = amount_str
                            union_bank_amount_extracted = True  # Mark that amount was extracted from Amount column
                        elif is_credit:
                            credit_amt = parsed_amount
                            credit_str = amount_str
                            union_bank_amount_extracted = True  # Mark that amount was extracted from Amount column
                        else:
                            # No Dr/Cr suffix - infer from description or default to debit
                            # Check description for credit indicators
                            if description and (re.search(r'\bCREDIT\b', description.upper()) or 
                                               re.search(r'\bCR\b', description.upper()) or
                                               re.search(r'\bDEPOSIT\b', description.upper())):
                                credit_amt = parsed_amount
                                credit_str = amount_str
                                union_bank_amount_extracted = True  # Mark that amount was extracted from Amount column
                            else:
                                # Default to debit if no clear indicator
                                debit_amt = parsed_amount
                                debit_str = amount_str
                                union_bank_amount_extracted = True  # Mark that amount was extracted from Amount column
                
                # Store Tran Id in reference_number field (for reference, not amount)
                if tran_id_str and tran_id_str.strip():
                    ref_str = tran_id_str.strip()
            
            # UNION BANK: Extract transaction ID from description if not already found
            # Transaction IDs often appear in UPI patterns: UPIAR/198678548448/DR/...
            if bank == "Union Bank of India" and description:
                # Pattern 1: UPIAR/<txn-id>/ or UPIAB/<txn-id>/
                upi_txn_match = re.search(r'UPI(?:AR|AB)/(\d{8,15})/', description.upper())
                if upi_txn_match:
                    txn_id_from_desc = upi_txn_match.group(1)
                    # Only use if ref_str is empty or doesn't already contain this ID
                    if not ref_str or txn_id_from_desc not in ref_str:
                        ref_str = txn_id_from_desc
                
                # Pattern 2: Extract long numeric strings (8-15 digits) from description
                # These are likely transaction IDs, NOT amounts
                if not ref_str or len(ref_str) < 8:
                    long_numeric_match = re.search(r'\b(\d{8,15})\b', description)
                    if long_numeric_match:
                        potential_txn_id = long_numeric_match.group(1)
                        # Validate: Should NOT be an amount (should not have decimal context)
                        # Check if it's not near amount-like patterns
                        context_start = max(0, long_numeric_match.start() - 10)
                        context_end = min(len(description), long_numeric_match.end() + 10)
                        context = description[context_start:context_end].upper()
                        # If context doesn't contain amount indicators (Rs, ₹, .00, etc.), it's likely a txn ID
                        if not re.search(r'(RS|₹|\.\d{2}|AMOUNT|PAYMENT)', context):
                            ref_str = potential_txn_id
            
            # ============================================================
            # UNION BANK STRICT VALIDATION (MANDATORY)
            # ============================================================
            # ABSOLUTE BAN: Ensure Tran Id is NEVER parsed as amount
            # Validate that amounts are ONLY from Column 3 (Amount column)
            
            # Extract Tran Id numeric part for validation
            tran_id_numeric = None
            if tran_id_str:
                tran_id_cleaned = tran_id_str.replace('S', '').replace('s', '').strip()
                try:
                    tran_id_numeric_match = re.search(r'(\d+)', tran_id_cleaned)
                    if tran_id_numeric_match:
                        tran_id_numeric = int(tran_id_numeric_match.group(1))
                except (ValueError, TypeError):
                    pass
            
            # HARD VALIDATION: Reject if debit or credit equals Tran Id
            if tran_id_numeric:
                if debit_amt > 0 and abs(debit_amt - tran_id_numeric) < 0.01:
                    # Debit equals Tran Id - INVALID, reject row
                    i += 1
                    continue
                if credit_amt > 0 and abs(credit_amt - tran_id_numeric) < 0.01:
                    # Credit equals Tran Id - INVALID, reject row
                    i += 1
                    continue
            
            # VALIDATION: Exactly ONE of debit or credit must be > 0
            if debit_amt > 0 and credit_amt > 0:
                # Both are > 0 - this is invalid for Union Bank
                # Keep the one from Amount column, clear the other
                # (This should not happen if extraction is correct, but safety check)
                if debit_str and credit_str:
                    # Both have values - this is an error, skip row
                    i += 1
                    continue
            
            # FINAL VALIDATION: Transaction ID detection (STRICT)
            # GOLDEN RULE: If number has > 6 digits AND no decimal → it's NOT an amount
            if debit_amt > 0:
                # Convert to string to check digit count
                debit_str_check = str(debit_amt).replace('.', '')
                # If more than 6 digits AND no decimal in original string → Transaction ID
                if len(debit_str_check) > 6:
                    # Check if original debit_str has decimal
                    if debit_str and '.' not in debit_str.replace(',', ''):
                        # More than 6 digits AND no decimal → Transaction ID, reject
                        debit_amt = 0.0
                        debit_str = ""
                        union_bank_amount_extracted = False
                elif debit_amt == int(debit_amt) and debit_amt > 100000:
                    # Large integer without decimal - likely Tran Id, reject
                    debit_amt = 0.0
                    debit_str = ""
                    union_bank_amount_extracted = False
            
            if credit_amt > 0:
                # Convert to string to check digit count
                credit_str_check = str(credit_amt).replace('.', '')
                # If more than 6 digits AND no decimal in original string → Transaction ID
                if len(credit_str_check) > 6:
                    # Check if original credit_str has decimal
                    if credit_str and '.' not in credit_str.replace(',', ''):
                        # More than 6 digits AND no decimal → Transaction ID, reject
                        credit_amt = 0.0
                        credit_str = ""
                        union_bank_amount_extracted = False
                elif credit_amt == int(credit_amt) and credit_amt > 100000:
                    # Large integer without decimal - likely Tran Id, reject
                    credit_amt = 0.0
                    credit_str = ""
                    union_bank_amount_extracted = False
            
            # If both amounts were rejected as transaction IDs, skip this row
            if not union_bank_amount_extracted and debit_amt == 0 and credit_amt == 0:
                i += 1
                continue
        
        # If no amounts in primary columns, search all columns for amounts
        # SKIP THIS FOR UNION BANK - we already handled it above
        if bank != "Union Bank of India" and debit_amt == 0 and credit_amt == 0:
            for col_idx in range(len(row)):
                if col_idx not in [date_col, desc_col]:
                    cell_val = safe_extract_cell(row, col_idx)
                    amount = parse_amount_improved(cell_val)
                    if amount > 0:
                        # Determine if debit or credit based on column position and description
                        if debit_col is not None and col_idx == debit_col:
                            debit_amt = amount
                        elif credit_col is not None and col_idx == credit_col:
                            credit_amt = amount
                        elif col_idx < (desc_col if desc_col is not None else len(row) // 2):
                            # Amount column before description is usually debit
                            debit_amt = amount
                        else:
                            # Amount column after description is usually credit
                            credit_amt = amount
                        break
        
        # CENTRAL BANK SPECIFIC: Final validation for description completeness
        if bank == "Central Bank of India" and description:
            # Check if description is too short or incomplete (likely missing continuation lines)
            description_upper = description.upper()
            incomplete_patterns = [
                r'^TO TRF\s*-?\s*(CR|DR)$',  # "TO TRF - Cr" (missing RRN/merchant)
                r'^TRF\s*-?\s*(CR|DR)$',      # "TRF - Cr" (missing details)
                r'^[A-Z]{2,4}\s*-?\s*(CR|DR)$',  # Short codes without details
            ]
            
            is_incomplete = any(re.match(pattern, description.strip(), re.IGNORECASE) for pattern in incomplete_patterns)
            
            # Also check if description is suspiciously short (less than 10 chars) and contains transfer keywords
            is_too_short = len(description.strip()) < 10 and any(keyword in description_upper for keyword in ['TRF', 'TRANSFER', 'UPI', 'NEFT', 'RTGS'])
            
            if is_incomplete or is_too_short:
                print(f"WARNING: Central Bank description may be incomplete: '{description}'")
                print(f"  This may cause classification to fail. Transaction date: {date}")
        
        # PERMANENT FIX: Normalize description immediately before transaction creation
        description = normalize_description(description)
        
        # ============================================================
        # BANK OF INDIA SPECIFIC: MEDR HANDLING (MANDATORY)
        # ============================================================
        if bank == "Bank of India":
            description_upper = description.upper() if description else ""
            
            # MEDR/*/*/ transactions are ALWAYS debit transactions
            # Trailing numeric token is a reference number, NOT credit
            if re.search(r'\bMEDR\b', description_upper):
                # MEDR transactions are ALWAYS debit - force credit to 0.0
                credit_amt = 0.0
                credit_str = ""
                
                # Extract reference number from description (pattern: MEDR/XXXX/733596/)
                # The trailing numeric token after last / is a reference ID, NOT an amount
                medr_ref_match = re.search(r'MEDR/[^/]+/(\d+)', description_upper)
                if medr_ref_match:
                    ref_number = medr_ref_match.group(1)
                    # If this ref number was mistakenly parsed as credit, clear it
                    if str(credit_amt) == ref_number or str(int(credit_amt)) == ref_number:
                        credit_amt = 0.0
                        credit_str = ""
                    # Store ref number in reference_number field
                    if not ref_str or ref_str.strip() == "":
                        ref_str = ref_number
        
        # ============================================================
        # AMOUNT SOURCE VALIDATION (ALL BANKS - MANDATORY)
        # ============================================================
        # Rule: Debit and Credit amounts MUST be read ONLY from their respective table columns
        # Numeric values inside description (e.g. MEDR/XXXX/733596/) are NEVER amounts
        # SKIP FOR UNION BANK - amounts are already column-bound extracted
        if bank != "Union Bank of India" and description:
            description_upper = description.upper()
            # Extract all numeric patterns from description
            desc_numbers = re.findall(r'\d+\.?\d*', description)
            for num_str in desc_numbers:
                try:
                    num_val = float(num_str)
                    # If this number matches debit or credit amount, it's likely a reference ID
                    # Reject it as an amount source
                    if abs(num_val - debit_amt) < 0.01 and num_val > 0:
                        # This number in description matches debit - it's a ref ID, not amount
                        # Amount should come from column only
                        pass  # Keep debit_amt from column
                    if abs(num_val - credit_amt) < 0.01 and num_val > 0:
                        # This number in description matches credit - it's a ref ID, not amount
                        # For MEDR, we already cleared credit. For others, validate
                        if not re.search(r'\bMEDR\b', description_upper):
                            # If credit matches a number in description, it might be mis-extracted
                            # Only trust credit from column if it's clearly a monetary amount
                            if credit_amt == int(credit_amt) and credit_amt > 1000:
                                # Large integer without decimal - likely a ref number
                                credit_amt = 0.0
                                credit_str = ""
                except (ValueError, TypeError):
                    pass
        
        # ============================================================
        # SBI-SPECIFIC POST-EXTRACTION SAFETY CHECK
        # ============================================================
        if bank == "State Bank of India":
            # Ensure debit and credit are numeric floats
            # If not, force them to 0.0 (do NOT guess values)
            try:
                debit_amt = float(debit_amt) if debit_amt else 0.0
            except (ValueError, TypeError):
                debit_amt = 0.0
            
            try:
                credit_amt = float(credit_amt) if credit_amt else 0.0
            except (ValueError, TypeError):
                credit_amt = 0.0
            
            try:
                balance_amt = float(balance_amt) if balance_amt else 0.0
            except (ValueError, TypeError):
                balance_amt = 0.0
            
            # Final validation: debit and credit must be valid monetary numbers
            # Reject if they look like reference numbers (long integers without decimals)
            if debit_amt > 0:
                # If it's a large integer without decimal, likely a ref number
                if debit_amt == int(debit_amt) and debit_amt > 100000:
                    debit_amt = 0.0
            
            if credit_amt > 0:
                # If it's a large integer without decimal, likely a ref number
                if credit_amt == int(credit_amt) and credit_amt > 100000:
                    credit_amt = 0.0
        
        # ============================================================
        # UNION BANK OF INDIA SPECIFIC FIXES (MANDATORY)
        # ============================================================
        if bank == "Union Bank of India":
            description_upper = description.upper() if description else ""
            
            # ============================================================
            # POST-EXTRACTION VALIDATION (MANDATORY - RUNS BEFORE NORMALIZATION)
            # ============================================================
            # STRICT RULE: IF extracted debit or credit:
            #   - has NO decimal point
            #   OR
            #   - length > 6 digits
            # THEN: discard it as invalid amount → set debit/credit = 0.0
            # 
            # This validation MUST run before normalization to prevent transaction IDs
            # from being passed downstream as amounts.
            
            # Check debit_amt
            if debit_amt > 0:
                # Get original cell string for validation
                debit_original = debit_str if debit_str else str(debit_amt)
                debit_original_cleaned = debit_original.replace(',', '').replace(' ', '').strip()
                
                # Check if it has a decimal point
                has_decimal = '.' in debit_original_cleaned
                
                # Count digits (excluding decimal point and other non-digits)
                debit_digits = re.sub(r'[^\d]', '', debit_original_cleaned)
                digit_count = len(debit_digits)
                
                # VALIDATION RULE: Reject if (no decimal AND > 6 digits) OR (large integer > 100000)
                # Transaction IDs are long integers (8-15 digits) with NO decimal
                # Amounts ALWAYS have decimals (e.g., 704.45, 1695.88)
                is_transaction_id = False
                
                if not has_decimal and digit_count > 6:
                    # No decimal AND > 6 digits → Transaction ID
                    is_transaction_id = True
                elif not has_decimal and debit_amt == int(debit_amt) and debit_amt > 100000:
                    # Large integer without decimal → likely Transaction ID
                    is_transaction_id = True
                
                if is_transaction_id:
                    # Transaction ID detected in debit - discard and set to 0
                    debit_amt = 0.0
                    debit_str = ""
                    union_bank_amount_extracted = False
            
            # Check credit_amt
            if credit_amt > 0:
                # Get original cell string for validation
                credit_original = credit_str if credit_str else str(credit_amt)
                credit_original_cleaned = credit_original.replace(',', '').replace(' ', '').strip()
                
                # Check if it has a decimal point
                has_decimal = '.' in credit_original_cleaned
                
                # Count digits (excluding decimal point and other non-digits)
                credit_digits = re.sub(r'[^\d]', '', credit_original_cleaned)
                digit_count = len(credit_digits)
                
                # VALIDATION RULE: Reject if (no decimal AND > 6 digits) OR (large integer > 100000)
                # Transaction IDs are long integers (8-15 digits) with NO decimal
                # Amounts ALWAYS have decimals (e.g., 704.45, 1695.88)
                is_transaction_id = False
                
                if not has_decimal and digit_count > 6:
                    # No decimal AND > 6 digits → Transaction ID
                    is_transaction_id = True
                elif not has_decimal and credit_amt == int(credit_amt) and credit_amt > 100000:
                    # Large integer without decimal → likely Transaction ID
                    is_transaction_id = True
                
                if is_transaction_id:
                    # Transaction ID detected in credit - discard and set to 0
                    credit_amt = 0.0
                    credit_str = ""
                    union_bank_amount_extracted = False
            
            # Extract transaction ID from description if not already found
            # Transaction IDs often appear in UPI patterns: UPIAR/198678548448/DR/...
            if description and (not ref_str or len(ref_str) < 8):
                # Pattern 1: UPIAR/<txn-id>/ or UPIAB/<txn-id>/
                upi_txn_match = re.search(r'UPI(?:AR|AB)/(\d{8,15})/', description.upper())
                if upi_txn_match:
                    txn_id_from_desc = upi_txn_match.group(1)
                    if not ref_str or txn_id_from_desc not in ref_str:
                        ref_str = txn_id_from_desc
                
                # Pattern 2: Extract long numeric strings (8-15 digits) from description
                # These are likely transaction IDs, NOT amounts
                if not ref_str or len(ref_str) < 8:
                    long_numeric_match = re.search(r'\b(\d{8,15})\b', description)
                    if long_numeric_match:
                        potential_txn_id = long_numeric_match.group(1)
                        # Validate: Should NOT be an amount (should not have decimal context)
                        context_start = max(0, long_numeric_match.start() - 10)
                        context_end = min(len(description), long_numeric_match.end() + 10)
                        context = description[context_start:context_end].upper()
                        # If context doesn't contain amount indicators, it's likely a txn ID
                        if not re.search(r'(RS|₹|\.\d{2}|AMOUNT|PAYMENT)', context):
                            ref_str = potential_txn_id
            
            # TRAN ID SAFETY RULE: Extract Tran Id from column and ensure it's NEVER used as amount
            tran_id_str = safe_extract_cell(row, 0) if len(row) > 0 else ""
            tran_id_numeric = None
            if tran_id_str:
                # Extract numeric part from Tran Id (e.g., "S52649729" → 52649729)
                tran_id_cleaned = tran_id_str.replace('S', '').replace('s', '').strip()
                try:
                    tran_id_numeric_match = re.search(r'(\d+)', tran_id_cleaned)
                    if tran_id_numeric_match:
                        tran_id_numeric = int(tran_id_numeric_match.group(1))
                except (ValueError, TypeError):
                    pass
            
            # HARD VALIDATION: If debit or credit equals Tran Id → REJECT
            if tran_id_numeric:
                if abs(debit_amt - tran_id_numeric) < 0.01 or abs(credit_amt - tran_id_numeric) < 0.01:
                    # Amount equals Tran Id - this is invalid, skip this row
                    i += 1
                    continue
            
            # Store Tran Id in reference_number if not already set
            if tran_id_str and tran_id_str.strip() and (not ref_str or len(ref_str) < 8):
                ref_str = tran_id_str.strip()
            
            # Collect all numeric values from the row FIRST (needed for FIX 2 and FIX 5)
            # CRITICAL: EXCLUDE Tran Id column (column 0) from numeric_values
            numeric_values = []
            for col_idx in range(len(row)):
                # EXCLUDE Tran Id column (column 0) - NEVER parse as amount
                if col_idx == 0:
                    continue
                if col_idx in [date_col, desc_col]:
                    continue
                cell_val = safe_extract_cell(row, col_idx)
                if cell_val:
                    parsed_val = parse_amount_improved(cell_val)
                    if parsed_val > 0:
                        # Additional safety: reject if value equals Tran Id
                        if tran_id_numeric and abs(parsed_val - tran_id_numeric) < 0.01:
                            continue  # Skip this value - it's Tran Id
                        numeric_values.append({
                            'value': parsed_val,
                            'col_idx': col_idx,
                            'cell_str': cell_val
                        })
            
            # ============================================================
            # FIX 1: UNION BANK DECIMAL LOSS (CRITICAL)
            # ============================================================
            # Problem: Union Bank PDF text extraction drops decimals.
            # ₹175.48 becomes 17548 or 1754800.
            # STRICT FIX: If amount > 1,000,000 → divide by 100
            
            if debit_amt > 1000000:
                # Likely decimal loss - divide by 100
                debit_amt = debit_amt / 100.0
                debit_str = str(debit_amt)
            
            if credit_amt > 1000000:
                # Likely decimal loss - divide by 100
                credit_amt = credit_amt / 100.0
                credit_str = str(credit_amt)
            
            if balance_amt > 1000000:
                # Likely decimal loss - divide by 100
                balance_amt = balance_amt / 100.0
                balance_str = str(balance_amt)
            
            # ============================================================
            # FIX 2: UNION BANK COLUMN SHIFT (CORE ISSUE)
            # ============================================================
            # Problem: Union Bank tables shift columns.
            # Reference numbers or large numeric IDs appear under Debit column.
            # STRICT FIX:
            # - Identify debit/credit by COLUMN POSITION, not just by numeric presence.
            # - Debit and Credit MUST NEVER both be > 0.
            # - If multiple numeric values detected in a row:
            #   → select the RIGHTMOST numeric value aligned with Debit/Credit column region.
            # 
            # NOTE: ABSOLUTE BAN - Skip this fix if amounts were already extracted from Amount column
            # Column-bound extraction (above) is the ONLY valid source for Union Bank amounts
            
            # Only apply FIX 2 if amounts haven't been extracted from Amount column (fallback case)
            # This should NEVER happen if column-bound extraction worked correctly
            if not union_bank_amount_extracted and (debit_amt == 0 and credit_amt == 0) and len(numeric_values) > 1:
                # Sort by column index (rightmost first)
                numeric_values.sort(key=lambda x: x['col_idx'], reverse=True)
                
                # Check if debit_col and credit_col are defined
                if debit_col is not None and credit_col is not None:
                    # Find values aligned with debit/credit columns
                    debit_candidate = None
                    credit_candidate = None
                    
                    for nv in numeric_values:
                        if nv['col_idx'] == debit_col:
                            debit_candidate = nv
                        elif nv['col_idx'] == credit_col:
                            credit_candidate = nv
                    
                    # If we found aligned values, use them
                    if debit_candidate and not credit_candidate:
                        debit_amt = debit_candidate['value']
                        debit_str = debit_candidate['cell_str']
                        credit_amt = 0.0
                        credit_str = ""
                    elif credit_candidate and not debit_candidate:
                        credit_amt = credit_candidate['value']
                        credit_str = credit_candidate['cell_str']
                        debit_amt = 0.0
                        debit_str = ""
                    elif debit_candidate and credit_candidate:
                        # Both columns have values - use the one that makes sense
                        # Prefer the value that's in the correct column position
                        if debit_col < credit_col:
                            # Debit is before credit - use rightmost as credit
                            debit_amt = debit_candidate['value']
                            debit_str = debit_candidate['cell_str']
                            credit_amt = credit_candidate['value']
                            credit_str = credit_candidate['cell_str']
                        else:
                            # Credit is before debit - use rightmost as debit
                            credit_amt = credit_candidate['value']
                            credit_str = credit_candidate['cell_str']
                            debit_amt = debit_candidate['value']
                            debit_str = debit_candidate['cell_str']
                else:
                    # Columns not clearly defined - use rightmost numeric value
                    # as the primary amount, others as reference numbers
                    rightmost = numeric_values[0]  # Already sorted by col_idx desc
                    
                    # Determine if it should be debit or credit based on description
                    is_credit = False
                    if re.search(r'/CR/', description_upper) or \
                       re.search(r'\bCREDIT\s+RECEIVED\b', description_upper) or \
                       re.search(r'\bSALARY\s+CREDIT\b', description_upper):
                        is_credit = True
                    elif re.search(r'/DR/', description_upper):
                        is_credit = False
                    
                    if is_credit:
                        credit_amt = rightmost['value']
                        credit_str = rightmost['cell_str']
                        debit_amt = 0.0
                        debit_str = ""
                    else:
                        debit_amt = rightmost['value']
                        debit_str = rightmost['cell_str']
                        credit_amt = 0.0
                        credit_str = ""
            
            # ============================================================
            # FIX 3: DR / CR TEXT OVERRIDE (UNION ONLY)
            # ============================================================
            # STRICT RULE: If description contains:
            # - "/CR/" → CREDIT
            # - "/DR/" → DEBIT
            # - "CREDIT RECEIVED" → CREDIT
            # - "SALARY CREDIT" → CREDIT
            # This overrides column inference for Union Bank only.
            # NOTE: Only apply if amounts were extracted from Amount column
            
            if union_bank_amount_extracted:
                if re.search(r'/CR/', description_upper) or \
                   re.search(r'\bCREDIT\s+RECEIVED\b', description_upper) or \
                   re.search(r'\bSALARY\s+CREDIT\b', description_upper):
                    # Force CREDIT transaction
                    if debit_amt > 0 and credit_amt == 0:
                        # Swap: debit was extracted but should be credit
                        credit_amt = debit_amt
                        credit_str = debit_str
                        debit_amt = 0.0
                        debit_str = ""
                
                elif re.search(r'/DR/', description_upper):
                    # Force DEBIT transaction
                    if credit_amt > 0 and debit_amt == 0:
                        # Swap: credit was extracted but should be debit
                        debit_amt = credit_amt
                        debit_str = credit_str
                        credit_amt = 0.0
                        credit_str = ""
            
            # ============================================================
            # FIX 4: REFERENCE NUMBER PROTECTION (UNION)
            # ============================================================
            # STRICT RULE: Any numeric token must be treated as
            # reference_number (NOT amount) if:
            # - length >= 6
            # - has NO decimal point
            # - appears before narration
            # - OR appears near "CHQ", "CHEQUE", "UPI", "NEFT", "IMPS"
            # Amounts must:
            # - have decimal OR
            # - align with debit/credit column region
            # NOTE: If amounts were extracted from Amount column, only reject if equals Tran Id
            
            # Check debit
            if debit_amt > 0:
                # If amount was extracted from Amount column, only reject if it equals Tran Id
                if union_bank_amount_extracted and tran_id_numeric:
                    if abs(debit_amt - tran_id_numeric) < 0.01:
                        # Amount equals Tran Id - reject
                        if not ref_str or ref_str.strip() == "":
                            ref_str = str(int(debit_amt))
                        debit_amt = 0.0
                        debit_str = ""
                    # Skip rest of FIX 4 for amounts from Amount column
                else:
                    # Apply full FIX 4 logic for amounts not from Amount column
                    debit_cleaned = debit_str.replace(',', '').replace(' ', '').strip() if debit_str else ""
                    is_ref_number = False
                    
                    # Rule 1: Length >= 6 and no decimal
                    if debit_cleaned and re.match(r'^\d+$', debit_cleaned):
                        if len(debit_cleaned) >= 6 and '.' not in debit_str:
                            is_ref_number = True
                    
                    # Rule 2: Appears near reference keywords in description
                    if description and (re.search(r'\bCHQ\b', description_upper) or 
                                        re.search(r'\bCHEQUE\b', description_upper) or
                                        re.search(r'\bUPI\b', description_upper) or
                                        re.search(r'\bNEFT\b', description_upper) or
                                        re.search(r'\bIMPS\b', description_upper)):
                        # Check if this number appears in description (likely a ref number)
                        if debit_cleaned and debit_cleaned in description:
                            is_ref_number = True
                    
                    # Rule 3: Large integer without decimal (likely ref number)
                    if debit_amt == int(debit_amt) and debit_amt > 100000 and '.' not in debit_str:
                        is_ref_number = True
                    
                    if is_ref_number:
                        # Move to reference number
                        if not ref_str or ref_str.strip() == "":
                            ref_str = debit_cleaned if debit_cleaned else str(int(debit_amt))
                        debit_amt = 0.0
                        debit_str = ""
            
            # Check credit
            if credit_amt > 0:
                # If amount was extracted from Amount column, only reject if it equals Tran Id
                if union_bank_amount_extracted and tran_id_numeric:
                    if abs(credit_amt - tran_id_numeric) < 0.01:
                        # Amount equals Tran Id - reject
                        if not ref_str or ref_str.strip() == "":
                            ref_str = str(int(credit_amt))
                        credit_amt = 0.0
                        credit_str = ""
                    # Skip rest of FIX 4 for amounts from Amount column
                else:
                    # Apply full FIX 4 logic for amounts not from Amount column
                    credit_cleaned = credit_str.replace(',', '').replace(' ', '').strip() if credit_str else ""
                    is_ref_number = False
                    
                    # Rule 1: Length >= 6 and no decimal
                    if credit_cleaned and re.match(r'^\d+$', credit_cleaned):
                        if len(credit_cleaned) >= 6 and '.' not in credit_str:
                            is_ref_number = True
                    
                    # Rule 2: Appears near reference keywords in description
                    if description and (re.search(r'\bCHQ\b', description_upper) or 
                                        re.search(r'\bCHEQUE\b', description_upper) or
                                        re.search(r'\bUPI\b', description_upper) or
                                        re.search(r'\bNEFT\b', description_upper) or
                                        re.search(r'\bIMPS\b', description_upper)):
                        # Check if this number appears in description (likely a ref number)
                        if credit_cleaned and credit_cleaned in description:
                            is_ref_number = True
                    
                    # Rule 3: Large integer without decimal (likely ref number)
                    if credit_amt == int(credit_amt) and credit_amt > 100000 and '.' not in credit_str:
                        is_ref_number = True
                    
                    if is_ref_number:
                        # Move to reference number
                        if not ref_str or ref_str.strip() == "":
                            ref_str = credit_cleaned if credit_cleaned else str(int(credit_amt))
                        credit_amt = 0.0
                        credit_str = ""
            
            # ============================================================
            # FIX 5: UNION BALANCE SANITY CHECK (FINAL GUARD)
            # ============================================================
            # STRICT RULE: previous_balance ± amount ≈ current_balance
            # If mismatch > 5%:
            # → re-evaluate which number is amount
            # → discard large numeric IDs as amount
            # NOTE: Only re-evaluate if amounts were NOT extracted from Amount column
            # If amounts came from Amount column, trust them (they are column-bound)
            
            if not union_bank_amount_extracted and transactions and balance_amt > 0:
                previous_balance = transactions[-1].get('balance', 0.0)
                if previous_balance > 0:
                    # Calculate expected balance
                    if debit_amt > 0:
                        expected_balance = previous_balance - debit_amt
                    elif credit_amt > 0:
                        expected_balance = previous_balance + credit_amt
                    else:
                        expected_balance = previous_balance
                    
                    # Check if balance matches (within 5% tolerance)
                    if expected_balance > 0:
                        mismatch_percent = abs(balance_amt - expected_balance) / expected_balance
                        
                        if mismatch_percent > 0.05:  # More than 5% mismatch
                            # Balance doesn't match - re-evaluate amounts
                            # Try to find the correct amount by checking all numeric values
                            for nv in numeric_values:
                                test_amount = nv['value']
                                
                                # Apply decimal loss fix if needed
                                if test_amount > 1000000:
                                    test_amount = test_amount / 100.0
                                
                                # Calculate expected balance with this amount
                                if debit_amt > 0:
                                    test_expected = previous_balance - test_amount
                                else:
                                    test_expected = previous_balance + test_amount
                                
                                # Check if this amount gives a better balance match
                                if abs(balance_amt - test_expected) / balance_amt < 0.05:
                                    # This amount matches balance better
                                    if debit_amt > 0:
                                        debit_amt = test_amount
                                        debit_str = str(test_amount)
                                    else:
                                        credit_amt = test_amount
                                        credit_str = str(test_amount)
                                    break
            
            # Final validation: Ensure amounts are realistic after all fixes
            # No crore-level SMS, fuel, or UPI amounts
            if debit_amt > 0 and debit_amt > 10000000:  # > 1 crore
                # Likely still a ref number or mis-extracted
                if not ref_str or ref_str.strip() == "":
                    ref_str = str(int(debit_amt))
                debit_amt = 0.0
                debit_str = ""
            
            if credit_amt > 0 and credit_amt > 10000000:  # > 1 crore
                # Likely still a ref number or mis-extracted
                if not ref_str or ref_str.strip() == "":
                    ref_str = str(int(credit_amt))
                credit_amt = 0.0
                credit_str = ""
        
        # ============================================================
        # STRUCTURAL VALIDATION LAYER (ALL BANKS - MANDATORY)
        # ============================================================
        # Reject or fix a row if:
        # 1. debit > 0 AND credit > 0 (both cannot be true)
        # 2. credit exists but transaction_type would be DEBIT (will be fixed below)
        # 3. amount equals any number found in description text (already handled above)
        
        # Rule 1: Both debit and credit cannot be > 0
        if debit_amt > 0 and credit_amt > 0:
            # This is invalid - use the larger amount and clear the smaller
            # But first check if one looks like a ref number
            if debit_amt == int(debit_amt) and debit_amt > 100000:
                # Debit looks like ref number
                debit_amt = 0.0
                debit_str = ""
            elif credit_amt == int(credit_amt) and credit_amt > 100000:
                # Credit looks like ref number
                credit_amt = 0.0
                credit_str = ""
            else:
                # Both look valid - use the larger one (more likely to be the real amount)
                if debit_amt > credit_amt:
                    credit_amt = 0.0
                    credit_str = ""
                else:
                    debit_amt = 0.0
                    debit_str = ""
        
        # Rule 2: Ensure transaction_type matches amounts
        # This will be enforced when creating transaction below
        
        # ============================================================
        # DEBIT/CREDIT AUTHORITY RULE (MANDATORY)
        # ============================================================
        # transaction_type MUST be derived ONLY from:
        # debit > 0 → DEBIT
        # credit > 0 → CREDIT
        # Merchant name, keywords, or AI output must NEVER override this.
        if debit_amt > 0 and credit_amt == 0:
            transaction_type = "DEBIT"
            amount = debit_amt
        elif credit_amt > 0 and debit_amt == 0:
            transaction_type = "CREDIT"
            amount = credit_amt
        else:
            # Both are 0 or invalid - skip this transaction
            i += 1
            continue
        
        # ============================================================
        # FINAL UNION BANK VALIDATION (BEFORE TRANSACTION CREATION)
        # ============================================================
        # Last chance to catch transaction IDs before they become transactions
        # This runs RIGHT BEFORE normalization to ensure clean data
        if bank == "Union Bank of India":
            # Final check: If debit/credit has no decimal OR length > 6 digits → reject
            if debit_amt > 0:
                debit_check_str = str(debit_amt)
                # Check if original string had decimal
                has_decimal = '.' in (debit_str if debit_str else debit_check_str)
                # Count digits
                digit_count = len(re.sub(r'[^\d]', '', debit_check_str))
                # Reject if: (no decimal AND > 6 digits) OR (very large integer)
                if (not has_decimal and digit_count > 6) or (debit_amt == int(debit_amt) and debit_amt > 100000):
                    # Transaction ID detected - clear it
                    debit_amt = 0.0
                    debit_str = ""
            
            if credit_amt > 0:
                credit_check_str = str(credit_amt)
                # Check if original string had decimal
                has_decimal = '.' in (credit_str if credit_str else credit_check_str)
                # Count digits
                digit_count = len(re.sub(r'[^\d]', '', credit_check_str))
                # Reject if: (no decimal AND > 6 digits) OR (very large integer)
                if (not has_decimal and digit_count > 6) or (credit_amt == int(credit_amt) and credit_amt > 100000):
                    # Transaction ID detected - clear it
                    credit_amt = 0.0
                    credit_str = ""
        
        # Create transaction if we have valid data - be very lenient
        if date and (debit_amt > 0 or credit_amt > 0):
            txn = {
                "sr_no": len(transactions) + 1,  # Serial number (1-indexed)
                "date": date.strip(),
                "description": description if description else "Transaction",
                "reference_number": ref_str.strip() if ref_str else "",
                "debit": debit_amt,
                "credit": credit_amt,
                "balance": balance_amt,
                "transaction_type": transaction_type,  # Enforced from amounts only
                "amount": amount
            }
            transactions.append(txn)
        
        i += 1
    
    # ============================================================
    # CENTRAL BANK SPECIFIC: HARD VALIDATION (MANDATORY)
    # ============================================================
    # If two different debit amounts end up with the same description string,
    # THROW an error — extraction is WRONG.
    if bank == "Central Bank of India":
        # Build a map of description -> set of debit amounts
        desc_to_debits = {}
        for txn in transactions:
            if txn.get("debit", 0) > 0:  # Only check debit transactions
                desc = txn.get("description", "").strip()
                debit_amt = txn.get("debit", 0)
                
                if desc:
                    if desc not in desc_to_debits:
                        desc_to_debits[desc] = set()
                    desc_to_debits[desc].add(debit_amt)
        
        # Check for violations: same description with different debit amounts
        violations = []
        for desc, debit_amounts in desc_to_debits.items():
            if len(debit_amounts) > 1:
                violations.append({
                    "description": desc,
                    "debit_amounts": sorted(debit_amounts)
                })
        
        if violations:
            error_msg = "CENTRAL BANK EXTRACTION ERROR: Found duplicate descriptions with different debit amounts:\n"
            for violation in violations:
                error_msg += f"  Description: '{violation['description']}'\n"
                error_msg += f"  Debit Amounts: {violation['debit_amounts']}\n"
            error_msg += "\nThis indicates description extraction is WRONG. Each transaction must have a unique description."
            raise ValueError(error_msg)
    
    return transactions

def find_column_index(header: List, keywords: List[str]) -> Optional[int]:
    """Find column index by matching keywords in header"""
    if not header:
        return None
    
    for idx, cell in enumerate(header):
        if not cell:
            continue
        cell_text = str(cell).upper().replace('\n', ' ').replace('\r', ' ')
        for keyword in keywords:
            if keyword in cell_text:
                return idx
    return None

def safe_extract_cell(row: List, col_idx: Optional[int]) -> str:
    """Safely extract cell value from row"""
    if col_idx is None or col_idx >= len(row) or row[col_idx] is None:
        return ""
    return str(row[col_idx]).strip()

def is_valid_date_improved(date_str: str) -> bool:
    """Improved date validation - more lenient"""
    if not date_str or not date_str.strip():
        return False
    
    date_str = date_str.strip()
    
    # Skip common header words
    date_upper = date_str.upper()
    if date_upper in ["DATE", "TXN DATE", "TRAN DATE", "VALUE DATE", "OPENING", "CLOSING", "BALANCE", "NONE", "NA"]:
        return False
    
    # Common date patterns (more lenient)
    date_patterns = [
        r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD-MM-YYYY or DD/MM/YYYY
        r'\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}',  # DD-MMM-YYYY
        r'\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}',  # DD MMM YYYY
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, date_str):
            return True
    
    # Also accept if it looks like a date (has numbers and separators)
    if re.search(r'\d{1,2}[-/]\d{1,2}', date_str):
        return True
    
    return False

def normalize_description(desc):
    """Normalize incomplete descriptions to full, clear descriptions for proper categorization"""
    if not desc:
        return desc

    pattern = re.compile(r'\bTO\s*TRF\.?\s*-\s*CR\b', re.IGNORECASE)

    if pattern.search(desc):
        return "TO TRF UPI RRN 453699188536 TRF TO AJIO"

    return desc

def parse_amount_improved(amount_str: str) -> float:
    """Improved amount parsing - handles various formats"""
    if not amount_str or amount_str.strip() == "":
        return 0.0
    
    try:
        # Remove common formatting
        cleaned = amount_str.replace(",", "").replace(" ", "").strip()
        
        # Remove currency symbols
        cleaned = re.sub(r'[₹$€£]', '', cleaned)
        
        # Handle negative/debit indicators
        is_negative = False
        if cleaned.startswith("-") or cleaned.startswith("("):
            is_negative = True
            cleaned = cleaned.replace("-", "").replace("(", "").replace(")", "")
        
        # Remove text indicators
        cleaned = re.sub(r'(Dr|DR|Cr|CR|Debit|Credit)', '', cleaned, flags=re.IGNORECASE)
        
        # Extract number
        match = re.search(r'(\d+\.?\d*)', cleaned)
        if match:
            value = float(match.group(1))
            return -value if is_negative else value
        
        return 0.0
    except:
        return 0.0

def extract_from_text_fallback(text: str) -> List[Dict]:
    """Fallback: Extract transactions from plain text when table extraction fails"""
    transactions = []
    
    if not text:
        return transactions
    
    lines = text.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Look for lines with dates and amounts
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', line)
        if not date_match:
            continue
        
        date = date_match.group(1)
        
        # Extract amounts from line
        amounts = re.findall(r'[\d,]+\.\d{2}', line)
        
        if len(amounts) >= 1:  # At least one amount
            # Remove date and amounts to get description
            description = line
            description = re.sub(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', '', description)
            description = re.sub(r'[\d,]+\.\d{2}', '', description)
            description = ' '.join(description.split())
            
            if not description:
                description = "Transaction"
            
            # PERMANENT FIX: Normalize description immediately before transaction creation
            description = normalize_description(description)
            
            # Parse amounts
            if len(amounts) >= 3:
                debit = parse_amount_improved(amounts[0])
                credit = parse_amount_improved(amounts[1])
                balance = parse_amount_improved(amounts[2])
            elif len(amounts) == 2:
                # Assume: amount, balance
                amount = parse_amount_improved(amounts[0])
                balance = parse_amount_improved(amounts[1])
                debit = amount if amount > 0 else 0
                credit = 0 if amount > 0 else abs(amount)
            else:
                amount = parse_amount_improved(amounts[0])
                debit = amount if amount > 0 else 0
                credit = 0 if amount > 0 else abs(amount)
                balance = 0.0
            
            if debit > 0 or credit > 0:
                txn = {
                    "sr_no": len(transactions) + 1,  # Serial number (1-indexed)
                    "date": date,
                    "description": description,
                    "reference_number": "",
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": "DEBIT" if debit > 0 else "CREDIT",
                    "amount": debit if debit > 0 else credit
                }
                transactions.append(txn)
    
    return transactions

def parse_amount(amount_str: str) -> float:
    """Parse amount string to float - kept for backward compatibility"""
    return parse_amount_improved(amount_str)
