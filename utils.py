import json
from datetime import datetime, timedelta
from supabase import Client

class ExpenseUtils:
    
    @staticmethod
    def format_currency(amount: float, currency: str = "$") -> str:
        return f"{currency}{amount:,.2f}"
    
    @staticmethod
    def get_date_range(period: str = "month"):
        now = datetime.now()
        
        if period == "day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        
        return start, end
    
    @staticmethod
    async def get_expenses_by_period(supabase: Client, user_id: int, period: str = "month"):
        start, end = ExpenseUtils.get_date_range(period)
        
        result = supabase.table('expenses').select("*").eq('user_id', user_id)\
            .gte('date', start.isoformat())\
            .lte('date', end.isoformat())\
            .execute()
        
        return result.data
    
    @staticmethod
    def calculate_category_totals(expenses: list) -> dict:
        category_totals = {}
        
        for expense in expenses:
            category = expense.get('category', 'Other')
            amount = float(expense.get('amount', 0))
            category_totals[category] = category_totals.get(category, 0) + amount
        
        return category_totals
    
    @staticmethod
    def generate_summary_text(expenses: list, period: str = "month") -> str:
        if not expenses:
            return f"📊 You have no expenses registered in this {period}."
        
        total = sum(float(exp.get('amount', 0)) for exp in expenses)
        category_totals = ExpenseUtils.calculate_category_totals(expenses)
        
        summary = f"📊 {period.capitalize()} summary:\n\n"
        summary += f"💰 Total: {ExpenseUtils.format_currency(total)}\n"
        summary += f"📝 Number of expenses: {len(expenses)}\n\n"
        summary += "📋 By category:\n"
        
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        category_emojis = {
            'Food': '🍔',
            'Transportation': '🚗',
            'Entertainment': '🎬',
            'Services': '💡',
            'Health': '💊',
            'Shopping': '🛍️',
            'Other': '📦'
        }
        
        for category, amount in sorted_categories:
            emoji = category_emojis.get(category, '📦')
            percentage = (amount / total) * 100 if total > 0 else 0
            summary += f"{emoji} {category}: {ExpenseUtils.format_currency(amount)} ({percentage:.1f}%)\n"
        
        return summary
    
    @staticmethod
    def parse_expense_from_text(text: str) -> dict:
        import re
        
        amount_patterns = [
            r'\$?\s*(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*(?:pesos|dolares|dólares|dollars|usd)?',
        ]
        
        amount = 0
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                break
        
        return {
            'amount': amount,
            'description': text,
            'category': 'Other'
        }
