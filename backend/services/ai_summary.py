"""
AI-Powered Expense Summary Report Generator
Uses OpenAI to create comprehensive, human-readable expense analysis reports
"""

import os
from openai import OpenAI
from typing import Dict, List, Any
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = None

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
else:
    logger.warning("OPENAI_API_KEY not found in environment variables")

def generate_expense_summary(statement_data: Dict, transactions: List[Dict]) -> Dict[str, Any]:
    """
    Generate AI-powered expense summary report
    
    Args:
        statement_data: Statement metadata (bank_name, account_number, etc.)
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary containing AI-generated summary report
    """
    if not client:
        return {
            'success': False,
            'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file.',
            'fallback_summary': _generate_fallback_summary(statement_data, transactions)
        }
    
    try:
        # Prepare transaction summary for AI
        total_debit = sum(t.get('debit', 0) or 0 for t in transactions)
        total_credit = sum(t.get('credit', 0) or 0 for t in transactions)
        
        # Category breakdown
        category_spend = {}
        for txn in transactions:
            category = txn.get('category', 'Uncategorized')
            debit = txn.get('debit', 0) or 0
            if debit > 0:
                category_spend[category] = category_spend.get(category, 0) + debit
        
        # Top spending categories
        top_categories = sorted(category_spend.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Date range
        dates = [t.get('date', '') for t in transactions if t.get('date')]
        date_range = f"{min(dates)} to {max(dates)}" if dates else "N/A"
        
        # Build prompt for OpenAI
        prompt = f"""Analyze the following bank statement data and create a comprehensive, human-readable expense summary report.

**Statement Information:**
- Bank: {statement_data.get('bank_name', 'Unknown')}
- Account Number: {statement_data.get('account_number', 'N/A')}
- Account Holder: {statement_data.get('account_holder', 'N/A')}
- Period: {date_range}
- Total Transactions: {len(transactions)}

**Financial Overview:**
- Total Income (Credit): ₹{total_credit:,.2f}
- Total Expenses (Debit): ₹{total_debit:,.2f}
- Net Flow: ₹{total_credit - total_debit:,.2f}

**Top Spending Categories:**
{chr(10).join([f"- {cat}: ₹{amt:,.2f}" for cat, amt in top_categories])}

**Transaction Sample (first 10):**
{chr(10).join([f"- {t.get('date', 'N/A')}: {t.get('description', 'N/A')[:50]} - ₹{t.get('debit', 0) or 0:,.2f} ({t.get('category', 'Uncategorized')})" for t in transactions[:10]])}

Please create a comprehensive expense summary report that includes:

1. **Executive Summary**: A brief overview of spending patterns and financial health
2. **Spending Analysis**: Detailed breakdown of where money was spent
3. **Category Insights**: Analysis of top spending categories with actionable insights
4. **Trends & Patterns**: Identify any spending trends or patterns
5. **Recommendations**: Practical recommendations for better financial management
6. **Key Highlights**: Important observations about the spending behavior

Make the report:
- Easy to understand for non-financial users
- Actionable with specific recommendations
- Professional yet conversational
- Focused on helping the user understand their expenses better

Return the report as a JSON object with the following structure:
{{
  "executive_summary": "Brief overview...",
  "spending_analysis": "Detailed analysis...",
  "category_insights": "Category breakdown insights...",
  "trends_patterns": "Trends identified...",
  "recommendations": "Actionable recommendations...",
  "key_highlights": ["Highlight 1", "Highlight 2", ...]
}}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using cost-effective model
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial advisor and expense analysis expert. Create clear, actionable expense reports that help users understand their spending patterns and make better financial decisions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse response
        ai_content = response.choices[0].message.content
        
        # Try to parse as JSON, fallback to text
        try:
            import json
            # Clean up markdown code blocks if present
            ai_content = ai_content.replace('```json', '').replace('```', '').strip()
            summary_data = json.loads(ai_content)
        except json.JSONDecodeError:
            # If not JSON, create structured response from text
            summary_data = {
                'executive_summary': ai_content[:500],
                'spending_analysis': ai_content[500:1000] if len(ai_content) > 500 else '',
                'category_insights': '',
                'trends_patterns': '',
                'recommendations': '',
                'key_highlights': []
            }
        
        return {
            'success': True,
            'summary': summary_data,
            'metadata': {
                'total_debit': total_debit,
                'total_credit': total_credit,
                'net_flow': total_credit - total_debit,
                'transaction_count': len(transactions),
                'top_categories': [{'category': cat, 'amount': amt} for cat, amt in top_categories]
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to generate AI summary: {str(e)}',
            'fallback_summary': _generate_fallback_summary(statement_data, transactions)
        }

def _generate_fallback_summary(statement_data: Dict, transactions: List[Dict]) -> Dict[str, Any]:
    """Generate a basic summary when AI is not available"""
    total_debit = sum(t.get('debit', 0) or 0 for t in transactions)
    total_credit = sum(t.get('credit', 0) or 0 for t in transactions)
    
    category_spend = {}
    for txn in transactions:
        category = txn.get('category', 'Uncategorized')
        debit = txn.get('debit', 0) or 0
        if debit > 0:
            category_spend[category] = category_spend.get(category, 0) + debit
    
    top_categories = sorted(category_spend.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'executive_summary': f"Your statement shows {len(transactions)} transactions with total expenses of ₹{total_debit:,.2f} and total income of ₹{total_credit:,.2f}.",
        'spending_analysis': f"The largest expense category is {top_categories[0][0] if top_categories else 'N/A'} with ₹{top_categories[0][1]:,.2f} in spending." if top_categories else "No spending data available.",
        'category_insights': f"Top spending categories: {', '.join([f'{cat} (₹{amt:,.2f})' for cat, amt in top_categories[:3]])}",
        'trends_patterns': 'Analyze your transaction history to identify spending patterns.',
        'recommendations': 'Review your top spending categories and consider setting budgets for high-expense areas.',
        'key_highlights': [
            f"Total expenses: ₹{total_debit:,.2f}",
            f"Total income: ₹{total_credit:,.2f}",
            f"Net flow: ₹{total_credit - total_debit:,.2f}",
        ]
    }

