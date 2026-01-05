"""
OpenAI-powered transaction normalizer with enterprise-grade classification
Uses 3-layer reasoning: Pattern → Semantic → Validation
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an Enterprise-grade Financial Transaction Classification Engine designed for Indian bank statements.
Your responsibility is to accurately interpret noisy, inconsistent, and previously unseen transaction descriptions and normalize them into structured financial metadata.
You must prioritize correctness, consistency, and explainability over guessing.

🧠 CORE PRINCIPLE (VERY IMPORTANT)
You must infer meaning from patterns, abbreviations, and context, not from memorized examples.
Assume:
* Descriptions may contain codes, IDs, noise, separators
* Merchant names may be partial, abbreviated, or embedded
* Bank formats differ across institutions
* New merchants appear frequently

🧱 MANDATORY 3-LAYER LOGIC (DO NOT SKIP)

🔹 Layer 1 — Pattern & Heuristic Reasoning (Deterministic)
Before any semantic inference:
* Identify payment rails: UPI, CARD, NEFT, IMPS, CASH
* Detect common financial intents:
   * Salary / Income
   * Subscription / Recurring
   * POS / Merchant purchase
   * Transfer / Self transfer
   * Charges / Fees
You must reason from:
* Keywords
* Prefixes/suffixes
* Separators (`/`, `-`, `_`)
* Known banking abbreviations

🔹 Layer 2 — Semantic AI Inference (Generalized)
If patterns alone are insufficient:
* Infer merchant identity from:
   * Linguistic similarity
   * Brand fragments
   * Transaction intent
* Normalize merchant to a human-readable brand or entity
* Map transaction to the closest applicable category
* Prefer best-fit category, not `"Others"`

You MUST handle previously unseen merchants logically.

🔹 Layer 3 — Logical Validation & Correction
After classification:
* Credit ≠ Expense
* Salary ≠ Debit
* Bank Charges ≠ Shopping
* Subscriptions ≠ Transfer
* Merchant should not be `Unknown` if any inference is possible

📚 ALLOWED CATEGORIES (EXHAUSTIVE & FINAL)
Use ONLY one of the following:
* Food
* Groceries
* Travel
* Transport
* Shopping
* Entertainment
* Utilities
* Healthcare
* Education
* Rent
* Salary
* Investment
* Insurance
* Cash Withdrawal
* Bank Charges
* Transfer
* Others

📤 OUTPUT FORMAT (STRICT JSON ONLY)
Return ONLY a JSON object:
{
  "merchant": "string",
  "category": "string",
  "channel": "UPI | CARD | NEFT | IMPS | CASH | BANK_TRANSFER | OTHER",
  "debit_or_credit": "debit | credit",
  "confidence": 0.0-1.0,
  "rationale": "short reason explaining inference"
}

🎯 DECISION RULES (CRITICAL)
* Do NOT default to `"Unknown"` unless inference is impossible
* If merchant is unclear, infer type of entity (e.g., "Online Subscription Service")
* Use `"Others"` category only as last resort
* Prefer semantic intent over literal tokens
* Be conservative but decisive

🔐 STRICT OUTPUT RULES
* ❌ No markdown
* ❌ No explanations outside JSON
* ❌ No arrays
* ❌ No invented data
* ❌ No changes to numeric fields

Apply layered reasoning, infer meaning from structure and context, validate logically, and return ONLY the final JSON object."""

def normalize_transaction_with_openai(txn: Dict) -> Dict:
    """
    Normalize transaction using OpenAI with enterprise-grade classification
    
    Args:
        txn: Transaction dict with date, description, debit, credit, balance
        
    Returns:
        Normalized dict with merchant, category, channel, confidence
    """
    
    # Prepare transaction for OpenAI
    transaction_input = {
        "date": txn.get("date", ""),
        "description": txn.get("description", ""),
        "debit": txn.get("debit", 0),
        "credit": txn.get("credit", 0),
        "balance": txn.get("balance", 0),
        "transaction_type": txn.get("transaction_type", "")
    }
    
    try:
        print("⚠️ OpenAI normalization invoked")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(transaction_input)}
            ],
            temperature=0,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        # Parse JSON
        normalized = json.loads(content)
        
        # Map to internal format (backwards compatibility)
        return {
            "merchant": normalized.get("merchant", "Unknown"),
            "category": normalized.get("category", "Others"),
            "channel": normalized.get("channel", "OTHER"),
            "debit_or_credit": normalized.get("debit_or_credit", "debit"),
            "confidence": normalized.get("confidence", 0.5),
            "rationale": normalized.get("rationale", "")
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print(f"Content: {content}")
        return fallback_normalization(txn)
    
    except Exception as e:
        # Treat invalid API key as a permanent failure (no retries, no silent fallback)
        error_text = str(e)
        status_code = getattr(e, "status_code", None)
        if status_code == 401 or "401" in error_text or "invalid_api_key" in error_text.lower():
            raise RuntimeError("Invalid OpenAI API key (401) — stopping further processing") from e

        print(f"OpenAI normalization error: {error_text}")
        return fallback_normalization(txn)

def fallback_normalization(txn: Dict) -> Dict:
    """Fallback to rule-based normalization if OpenAI fails"""
    from rule_based_normalizer import normalize_transaction
    result = normalize_transaction(txn)
    result["confidence"] = 0.3  # Lower confidence for fallback
    result["rationale"] = "Rule-based fallback"
    return result

# Backwards compatibility
def normalize_transaction(txn: Dict) -> Dict:
    """Wrapper for backwards compatibility"""
    return normalize_transaction_with_openai(txn)