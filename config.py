import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    CATEGORIES = [
        'Food',
        'Transportation',
        'Entertainment',
        'Services',
        'Health',
        'Shopping',
        'Salary',
        'Freelance',
        'Business',
        'Investment',
        'Gift',
        'Refund',
        'Other'
    ]
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append('TELEGRAM_BOT_TOKEN')
        if not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
        if not cls.SUPABASE_URL:
            missing.append('SUPABASE_URL')
        if not cls.SUPABASE_KEY:
            missing.append('SUPABASE_KEY')
        
        if missing:
            raise ValueError(f"Missing the following environment variables: {', '.join(missing)}")
        
        return True
