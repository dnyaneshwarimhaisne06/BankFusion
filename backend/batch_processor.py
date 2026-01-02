"""
Batch PDF Processor for BankFusion
Process single, multiple, or all bank statements at once
"""

import os
import json
import sys
import importlib.util
from pathlib import Path
# Import from the pdf_extractor.py file (not the package)
# The pdf_extractor package exists, but we need functions from pdf_extractor.py file
pdf_extractor_path = Path(__file__).parent / "pdf_extractor.py"
spec = importlib.util.spec_from_file_location("pdf_extractor_file", pdf_extractor_path)
pdf_extractor_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_extractor_file)
extract_transactions = pdf_extractor_file.extract_transactions
extract_account_info = pdf_extractor_file.extract_account_info
from hybrid_normalizer import normalize_transaction
from datetime import datetime

# Paths - Use project root (one level up from backend/)
PROJECT_ROOT = Path(__file__).parent.parent  # BankFusion/ directory
RAW_PDFS_DIR = PROJECT_ROOT / "data" / "raw_pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "normalized_json"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}→ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def build_json_structure(account_info, transactions):
    """Build JSON structure with normalized transactions - filters out null/invalid transactions"""
    
    # Filter out transactions with null/empty critical fields
    valid_transactions = []
    for txn in transactions:
        # Check if transaction has required fields
        date = txn.get('date') or txn.get('transaction_date')
        description = txn.get('description') or txn.get('narration')
        debit = txn.get('debit', 0) or txn.get('withdrawal', 0)
        credit = txn.get('credit', 0) or txn.get('deposit', 0)
        amount = txn.get('amount', 0)
        
        # Skip if date is null/empty or invalid
        if not date or not str(date).strip() or str(date).strip().upper() in ['NONE', 'NULL', 'NA', '']:
            continue
        
        # Skip if no amount (both debit and credit are 0 or null)
        if (not debit or debit == 0) and (not credit or credit == 0) and (not amount or amount == 0):
            continue
        
        # Ensure description is not empty
        if not description or not str(description).strip():
            description = "Transaction"
        
        # Clean and validate transaction
        clean_txn = {
            "date": str(date).strip(),
            "description": str(description).strip() if description else "Transaction",
            "reference_number": str(txn.get('reference_number', '')).strip() if txn.get('reference_number') else "",
            "debit": float(debit) if debit else 0.0,
            "credit": float(credit) if credit else 0.0,
            "balance": float(txn.get('balance', 0)) if txn.get('balance') else 0.0,
            "transaction_type": txn.get('transaction_type', 'DEBIT' if debit else 'CREDIT'),
            "amount": float(amount) if amount else (float(debit) if debit else float(credit))
        }
        
        valid_transactions.append(clean_txn)
    
    # Include all account fields even if None (as per user requirement)
    clean_account_info = {
        "account_number": account_info.get("account_number"),
        "account_holder": account_info.get("account_holder"),
        "statement_period": account_info.get("statement_period"),
        "branch": account_info.get("branch"),
        "ifsc": account_info.get("ifsc")
    }
    
    result = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_transactions": len(valid_transactions),
            "bank_name": account_info.get("bank_name") or "Unknown",
            "normalization_method": "hybrid"  # Uses hybrid_normalizer (rule-based + OpenAI + global rules)
        },
        "account": clean_account_info,
        "transactions": []
    }

    # Normalize transactions with progress tracking
    total_txns = len(valid_transactions)
    print_info(f"Normalizing {total_txns} transactions...")
    
    for idx, txn in enumerate(valid_transactions, 1):
        try:
            normalized = normalize_transaction(txn)
            result["transactions"].append({
                "original": txn,
                "normalized": normalized
            })
            
            # Show progress every 50 transactions
            if idx % 50 == 0 or idx == total_txns:
                print_info(f"  Progress: {idx}/{total_txns} transactions normalized...")
        except Exception as norm_error:
            print_error(f"Error normalizing transaction {idx}: {str(norm_error)}")
            # Continue with next transaction even if one fails
            result["transactions"].append({
                "original": txn,
                "normalized": {
                    "transaction_type": "unknown",
                    "merchant": "Unknown",
                    "channel": "OTHER",
                    "debit_or_credit": "debit",
                    "category": "others"
                }
            })
    
    # Calculate summary
    total_debit = sum(t.get('debit', 0) for t in valid_transactions)
    total_credit = sum(t.get('credit', 0) for t in valid_transactions)
    
    result["summary"] = {
        "total_transactions": len(valid_transactions),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "net_change": round(total_credit - total_debit, 2)
    }
    
    return result

def process_single_pdf(pdf_path, output_dir):
    """Process a single PDF file"""
    pdf_name = os.path.basename(pdf_path)
    print_info(f"Processing: {pdf_name}")
    
    try:
        # Extract data
        account_info = extract_account_info(pdf_path)
        transactions = extract_transactions(pdf_path)
        
        if not transactions:
            print_warning(f"No transactions found in {pdf_name}")
            return False
        
        print_info(f"Extracted {len(transactions)} transactions")
        
        # Build JSON
        print_info("Building JSON structure...")
        try:
            result = build_json_structure(account_info, transactions)
            print_info(f"JSON structure built successfully. Total transactions: {result['metadata']['total_transactions']}")
        except Exception as build_error:
            print_error(f"Failed to build JSON structure: {str(build_error)}")
            import traceback
            traceback.print_exc()
            return False
        
        # Save JSON
        json_filename = pdf_name.replace('.pdf', '.json')
        json_path = output_dir / json_filename
        
        # Ensure output directory exists
        print_info(f"Ensuring output directory exists: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        print_info(f"Output directory ready: {output_dir.exists()}")
        
        print_info(f"Attempting to save file: {json_path}")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # Verify file was created
            if json_path.exists():
                file_size = json_path.stat().st_size
                print_success(f"Saved: {json_filename}")
                print_info(f"  Full path: {json_path}")
                print_info(f"  File size: {file_size:,} bytes")
                print_info(f"  Bank: {account_info.get('bank_name', 'Unknown')}")
                print_info(f"  Transactions: {len(transactions)}")
                print_info(f"  Debit: ₹{result['summary']['total_debit']:,.2f}")
                print_info(f"  Credit: ₹{result['summary']['total_credit']:,.2f}")
            else:
                print_error(f"File was not created at: {json_path}")
                return False
        except Exception as save_error:
            print_error(f"Failed to save JSON file: {str(save_error)}")
            print_error(f"  Attempted path: {json_path}")
            print_error(f"  Output directory exists: {output_dir.exists()}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Failed to process {pdf_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def get_all_pdfs(base_dir):
    """Get all PDF files organized by bank"""
    banks = {}
    
    # Check for PDFs directly in base_dir (no bank subdirectories)
    direct_pdfs = list(base_dir.glob("*.pdf"))
    if direct_pdfs:
        banks["_direct"] = direct_pdfs
    
    # Check for PDFs in bank subdirectories
    for bank_dir in base_dir.iterdir():
        if bank_dir.is_dir() and not bank_dir.name.startswith('.'):
            bank_name = bank_dir.name
            pdf_files = list(bank_dir.glob("*.pdf"))
            if pdf_files:
                banks[bank_name] = pdf_files
    
    return banks

def process_bank(bank_name, base_dir, output_dir):
    """Process all PDFs for a specific bank"""
    # Handle PDFs directly in raw_pdfs directory
    if bank_name == "_direct":
        pdf_files = list(base_dir.glob("*.pdf"))
        bank_output_dir = output_dir
        display_name = "Direct PDFs"
    else:
        bank_dir = base_dir / bank_name
        
        if not bank_dir.exists():
            print_error(f"Bank directory not found: {bank_name}")
            return
        
        pdf_files = list(bank_dir.glob("*.pdf"))
        bank_output_dir = output_dir / bank_name
        display_name = f"{bank_name} Bank"
    
    if not pdf_files:
        print_warning(f"No PDF files found in {display_name}")
        return
    
    print_header(f"Processing {display_name}")
    print_info(f"Found {len(pdf_files)} PDF file(s)")
    
    # Create bank-specific output directory
    bank_output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    for pdf_path in pdf_files:
        if process_single_pdf(pdf_path, bank_output_dir):
            success_count += 1
        print()  # Empty line between files
    
    print_success(f"Completed: {success_count}/{len(pdf_files)} files processed successfully")

def process_all_banks(base_dir, output_dir):
    """Process all PDFs from all banks"""
    banks = get_all_pdfs(base_dir)
    
    if not banks:
        print_warning("No PDF files found in any bank directory")
        return
    
    print_header("Processing All Banks")
    total_files = sum(len(pdfs) for pdfs in banks.values())
    print_info(f"Found {len(banks)} bank(s) with {total_files} PDF file(s)")
    
    for bank_name in banks:
        print()
        process_bank(bank_name, base_dir, output_dir)
    
    print_header("Summary")
    for bank_name, pdfs in banks.items():
        if bank_name == "_direct":
            json_files = list(output_dir.glob("*.json"))
            display_name = "Direct PDFs"
        else:
            json_files = list((output_dir / bank_name).glob("*.json")) if (output_dir / bank_name).exists() else []
            display_name = bank_name
        print_info(f"{display_name}: {len(json_files)}/{len(pdfs)} processed")

def process_specific_file(file_path, output_dir):
    """Process a specific PDF file by path"""
    if not os.path.exists(file_path):
        print_error(f"File not found: {file_path}")
        return
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Output directory: {output_dir}")
    
    print_header("Processing Specific File")
    success = process_single_pdf(file_path, output_dir)
    
    if success:
        print_success(f"File processed and saved successfully!")
    else:
        print_error(f"Failed to process file. Check errors above.")

def show_menu():
    """Show interactive menu"""
    print_header("🏦 BankFusion Batch Processor")
    
    print(f"{Colors.BOLD}Available Options:{Colors.END}")
    print("  1. Process ALL banks (all PDF files)")
    print("  2. Process specific bank")
    print("  3. Process specific PDF file")
    print("  4. List available banks")
    print("  0. Exit")
    print()

def list_banks(base_dir):
    """List all available banks and their PDFs"""
    banks = get_all_pdfs(base_dir)
    
    print_header("Available Banks")
    
    if not banks:
        print_warning("No banks with PDF files found")
        return
    
    for bank_name, pdfs in banks.items():
        display_name = "Direct PDFs (root directory)" if bank_name == "_direct" else bank_name
        print(f"\n{Colors.BOLD}{Colors.CYAN}{display_name}:{Colors.END}")
        for pdf in pdfs:
            print(f"  • {pdf.name}")
    
    print()

def main():
    """Main function"""
    
    # Check if running with command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "all":
            process_all_banks(RAW_PDFS_DIR, OUTPUT_DIR)
        
        elif command == "bank" and len(sys.argv) > 2:
            bank_name = sys.argv[2]
            process_bank(bank_name, RAW_PDFS_DIR, OUTPUT_DIR)
        
        elif command == "file" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            process_specific_file(file_path, OUTPUT_DIR)
        
        elif command == "list":
            list_banks(RAW_PDFS_DIR)
        
        else:
            print("Usage:")
            print("  python batch_processor.py all              - Process all banks")
            print("  python batch_processor.py bank HDFC        - Process specific bank")
            print("  python batch_processor.py file path.pdf    - Process specific file")
            print("  python batch_processor.py list             - List available banks")
        
        return
    
    # Interactive mode
    while True:
        show_menu()
        choice = input(f"{Colors.BOLD}Enter your choice: {Colors.END}").strip()
        
        if choice == "0":
            print_info("Goodbye!")
            break
        
        elif choice == "1":
            process_all_banks(RAW_PDFS_DIR, OUTPUT_DIR)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        
        elif choice == "2":
            list_banks(RAW_PDFS_DIR)
            bank_name = input(f"\n{Colors.BOLD}Enter bank name: {Colors.END}").strip()
            if bank_name:
                process_bank(bank_name, RAW_PDFS_DIR, OUTPUT_DIR)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        
        elif choice == "3":
            file_path = input(f"{Colors.BOLD}Enter PDF file path: {Colors.END}").strip()
            if file_path:
                process_specific_file(file_path, OUTPUT_DIR)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        
        elif choice == "4":
            list_banks(RAW_PDFS_DIR)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        
        else:
            print_error("Invalid choice!")
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")

if __name__ == "__main__":
    main()