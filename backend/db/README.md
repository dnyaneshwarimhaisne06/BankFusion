# MongoDB Bank Statements Storage

## Architecture

**Polymorphic Parent + Normalized Transactions (Hybrid Model)**

### Collections

1. **`bank_statements`** - One document per statement (polymorphic parent)
   - Contains `bankType` (SBI|HDFC|BOI|CBI|UNION|AXIS)
   - Stores account + statement-level data
   - Bank-specific fields in `bankSpecific.<bankCode>`
   - `_id` used as `statementId` for transactions

2. **`bank_transactions`** - One document per transaction (normalized)
   - 300 transactions per statement
   - Every document includes:
     - `statementId` (from parent)
     - `bankType` (matching parent)
     - Same schema for all banks:
       - `date` (ISODate)
       - `amount` (float)
       - `direction` (debit/credit)
       - `balance` (float)
       - `channel` (UPI/CARD/ATM/BANK_TRANSFER)
       - `merchant` (string, no IDs)
       - `category` (string, no "Unknown" or "others")
       - `reference` (string)
       - `description` (string)

## Anti-Mixing Rules

- One statement = one `statementId`
- All 300 transactions use SAME `statementId`
- `bankType` must always match parent
- No transaction mixing across statements

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export MONGO_URI="mongodb://localhost:27017"
export DATABASE_NAME="bankfusion_db"
```

## Usage

```bash
# Insert all JSON files from data/normalized_json
python insert_bank_statements.py
```

## Files

- `schema.py` - MongoDB schema definitions and normalization functions
- `insert_bank_statements.py` - Main insertion script
- `config.py` - MongoDB configuration
- `requirements.txt` - Python dependencies

