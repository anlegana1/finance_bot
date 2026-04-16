import os
import logging
import json
import base64
import sys
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client, Client
import supabase
from config import Config
import httpx

try:
    Config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please copy .env.example to .env and configure your credentials.")
    exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout,
    force=True
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


def format_transaction_label(transaction_type: str) -> str:
    return "Income" if transaction_type == "income" else "Expense"


def default_category_for_type(transaction_type: str) -> str:
    return "Salary" if transaction_type == "income" else "Other"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
Welcome to the Finance Tracker Bot! 💰

I can help you track both expenses and income in multiple ways:
📝 Text: "Bought coffee for $5" or "Received salary of $1200"
📸 Photo: Send a picture of your receipt
🎤 Audio: Record a voice message describing the transaction

Available commands:
/start - Show this message
/summary - View monthly finance summary
/categories - View all categories

Send your first transaction!
    """
    await update.message.reply_text(welcome_message)

async def categorize_transaction(description: str) -> dict:
    try:
        prompt = f"""
Analyze the following financial transaction and extract information in JSON format:
"{description}"

Return ONLY a JSON object with this exact structure:
{{
    "transaction_type": "expense or income",
    "amount": number (without currency symbols),
    "description": "brief and clear description of the transaction",
    "category": "for expenses use one of: Food, Transportation, Entertainment, Services, Health, Shopping, Other; for income use one of: Salary, Freelance, Business, Investment, Gift, Refund, Other",
    "date": "YYYY-MM-DD format if a date is mentioned, or null if no date is mentioned"
}}

If the amount cannot be determined, use 0.
If no date is mentioned in the text, use null for date.
Current date is {datetime.now().strftime('%Y-%m-%d')} for reference.
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that classifies financial transactions as income or expense and categorizes them. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        if result.get("transaction_type") not in ["income", "expense"]:
            result["transaction_type"] = "expense"
        if not result.get("category"):
            result["category"] = default_category_for_type(result["transaction_type"])
        return result
    except Exception as e:
        logger.error(f"Error categorizing transaction: {e}")
        return {
            "transaction_type": "expense",
            "amount": 0,
            "description": description,
            "category": "Other",
            "currency": "CAD",
            "date": None
        }

async def save_expense(user_id: int, username: str, expense_data: dict):
    try:
        transaction_date = expense_data.get("date")
        if transaction_date:
            try:
                from dateutil import parser
                parsed_date = parser.parse(transaction_date)
                date_iso = parsed_date.isoformat()
            except:
                date_iso = datetime.now().isoformat()
        else:
            date_iso = datetime.now().isoformat()
        
        data = {
            "user_id": user_id,
            "username": username,
            "transaction_type": expense_data["transaction_type"],
            "amount": expense_data["amount"],
            "currency": "CAD",
            "description": expense_data["description"],
            "category": expense_data["category"],
            "date": date_iso
        }
        
        result = supabase.table('expenses').insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving expense: {e}")
        return False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    text = update.message.text
    
    await update.message.reply_text("⏳ Processing your transaction...")
    
    expense_data = await categorize_transaction(text)
    
    if await save_expense(user_id, username, expense_data):
        transaction_label = format_transaction_label(expense_data["transaction_type"])
        response = f"""
✅ {transaction_label} registered successfully!

💵 Amount: ${expense_data['amount']:.2f}
📋 Description: {expense_data['description']}
🏷️ Category: {expense_data['category']}
🔄 Type: {expense_data['transaction_type'].capitalize()}
        """
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("❌ Error saving transaction. Please try again.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    await update.message.reply_text("📸 Processing receipt image...")
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    photo_path = f"temp_{user_id}_{datetime.now().timestamp()}.jpg"
    await file.download_to_drive(photo_path)
    
    try:
        import base64
        
        with open(photo_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this receipt or transaction proof and extract the information in JSON format:
{
    "transaction_type": "expense or income",
    "amount": total number,
    "description": "transaction description",
    "category": "for expenses use one of: Food, Transportation, Entertainment, Services, Health, Shopping, Other; for income use one of: Salary, Freelance, Business, Investment, Gift, Refund, Other"
}
Respond ONLY with JSON."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        expense_data = json.loads(response.choices[0].message.content)
        if expense_data.get("transaction_type") not in ["income", "expense"]:
            expense_data["transaction_type"] = "expense"
        if not expense_data.get("category"):
            expense_data["category"] = default_category_for_type(expense_data["transaction_type"])
        
        if await save_expense(user_id, username, expense_data):
            transaction_label = format_transaction_label(expense_data["transaction_type"])
            response_text = f"""
✅ {transaction_label} from photo registered!

💵 Amount: ${expense_data['amount']:.2f}
📋 Description: {expense_data['description']}
🏷️ Category: {expense_data['category']}
🔄 Type: {expense_data['transaction_type'].capitalize()}
            """
            await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("❌ Error saving transaction.")
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text("❌ Error processing image. Please try with text.")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    await update.message.reply_text("🎤 Processing your voice message...")
    
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    
    voice_path = f"temp_{user_id}_{datetime.now().timestamp()}.ogg"
    await file.download_to_drive(voice_path)
    
    try:
        with open(voice_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        
        transcribed_text = transcript.text
        await update.message.reply_text(f"📝 I heard: \"{transcribed_text}\"")
        
        expense_data = await categorize_transaction(transcribed_text)
        
        if await save_expense(user_id, username, expense_data):
            transaction_label = format_transaction_label(expense_data["transaction_type"])
            response = f"""
✅ {transaction_label} from audio registered!

💵 Amount: ${expense_data['amount']:.2f}
📋 Description: {expense_data['description']}
🏷️ Category: {expense_data['category']}
🔄 Type: {expense_data['transaction_type'].capitalize()}
            """
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ Error saving transaction.")
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        await update.message.reply_text("❌ Error processing audio. Please try with text.")
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        current_month = datetime.now().strftime('%Y-%m')
        
        result = supabase.table('expenses').select("*").eq('user_id', user_id).gte('date', f'{current_month}-01').execute()
        
        if not result.data:
            await update.message.reply_text("📊 You have no transactions registered this month.")
            return
        
        income_total = sum(item['amount'] for item in result.data if item['transaction_type'] == 'income')
        expense_total = sum(item['amount'] for item in result.data if item['transaction_type'] == 'expense')
        net_total = income_total - expense_total
        
        categories = {}
        for item in result.data:
            key = f"{item['transaction_type'].capitalize()} - {item['category']}"
            categories[key] = categories.get(key, 0) + item['amount']
        
        summary_text = f"📊 Monthly summary:\n\n💸 Expenses: ${expense_total:.2f}\n💰 Income: ${income_total:.2f}\n🧮 Net: ${net_total:.2f}\n\n📋 By type and category:\n"
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            summary_text += f"• {cat}: ${amount:.2f}\n"
        
        await update.message.reply_text(summary_text)
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        await update.message.reply_text("❌ Error getting summary.")

async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories_text = """
🏷️ Available categories:

Expense categories:
• Food 🍔
• Transportation 🚗
• Entertainment 🎬
• Services 💡
• Health 💊
• Shopping 🛍️
• Other 📦

Income categories:
• Salary 💼
• Freelance 🧑‍💻
• Business 🏢
• Investment 📈
• Gift 🎁
• Refund 🔁
• Other 📦

Categories are assigned automatically based on your description.
    """
    await update.message.reply_text(categories_text)

def main():
    try:
        from threading import Thread
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import time
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Bot is running')
            
            def log_message(self, format, *args):
                pass
        
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        
        def run_server():
            logger.info(f"✅ HTTP server started on port {port}")
            server.serve_forever()
        
        logger.info(f"Starting HTTP server on port {port}...")
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)
        
        logger.info("Starting Telegram application build...")
        app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("summary", summary))
        app.add_handler(CommandHandler("categories", categories))
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        logger.info("✅ Bot started successfully...")
        logger.info("🤖 Waiting for messages...")
        
        while True:
            try:
                app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            except Exception as poll_error:
                logger.error(f"⚠️ Polling error: {poll_error}")
                logger.info("🔄 Reconnecting in 5 seconds...")
                time.sleep(5)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()
