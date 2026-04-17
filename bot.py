import os
import logging
import json
import base64
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
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

EDIT_AMOUNT, EDIT_CATEGORY, EDIT_DESCRIPTION, EDIT_DATE = range(4)

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
/edit - Edit or delete your recent transactions
/cancel - Cancel current operation

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
    
    logger.info(f"handle_text called with: '{text}' by user {user_id}")
    
    # Suggest using command format for common commands
    text_lower = text.strip().lower()
    if text_lower in ['edit', 'summary', 'categories', 'cancel']:
        await update.message.reply_text(f"💡 Use: /{text_lower}")
        return
    
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

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"edit_command started for user {user_id}")
    
    try:
        result = supabase.table('expenses').select("*").eq('user_id', user_id).order('created_at', desc=True).limit(5).execute()
        logger.info(f"Fetched {len(result.data) if result.data else 0} transactions")
        
        if not result.data:
            await update.message.reply_text("📭 You have no registered transactions.")
            logger.info("No transactions found, ending conversation")
            return ConversationHandler.END
        
        keyboard = []
        for expense in result.data:
            date_str = expense['date'][:10] if expense.get('date') else 'No date'
            button_text = f"${expense['amount']:.2f} - {expense['category']} - {date_str}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_{expense['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📋 Select the transaction you want to edit:",
            reply_markup=reply_markup
        )
        logger.info("Returning state 0 - waiting for transaction selection")
        return 0
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        await update.message.reply_text("❌ Error fetching transactions.")
        return ConversationHandler.END

async def select_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles transaction selection from the edit menu"""
    logger.info("✅ select_transaction CALLED")
    query = update.callback_query
    logger.info(f"Callback data: {query.data}")
    await query.answer()
    logger.info("Query answered")
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    expense_id = int(query.data.split("_")[1])
    context.user_data['editing_id'] = expense_id
    
    try:
        result = supabase.table('expenses').select("*").eq('id', expense_id).execute()
        
        if not result.data:
            await query.edit_message_text("❌ Transaction not found.")
            return ConversationHandler.END
        
        expense = result.data[0]
        context.user_data['current_expense'] = expense
        
        keyboard = [
            [InlineKeyboardButton("💵 Amount", callback_data="edit_amount")],
            [InlineKeyboardButton("🏷️ Category", callback_data="edit_category")],
            [InlineKeyboardButton("📋 Description", callback_data="edit_description")],
            [InlineKeyboardButton("📅 Date", callback_data="edit_date")],
            [InlineKeyboardButton("🗑️ Delete", callback_data="delete")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📝 Editing transaction:

💵 Amount: ${expense['amount']:.2f}
🏷️ Category: {expense['category']}
📋 Description: {expense['description']}
📅 Date: {expense.get('date', 'N/A')[:10]}

What do you want to modify?
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        logger.info("Returning state 1 - waiting for field selection")
        return 1
        
    except Exception as e:
        logger.error(f"Error loading transaction: {e}")
        await query.edit_message_text("❌ Error loading transaction.")
        return ConversationHandler.END

async def edit_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("✅ edit_field_selection CALLED")
    query = update.callback_query
    logger.info(f"Callback data: {query.data}")
    await query.answer()
    logger.info("Query answered")
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    if query.data == "delete":
        expense_id = context.user_data.get('editing_id')
        try:
            supabase.table('expenses').delete().eq('id', expense_id).execute()
            await query.edit_message_text("✅ Transaction deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting: {e}")
            await query.edit_message_text("❌ Error deleting transaction.")
        return ConversationHandler.END
    
    if query.data == "edit_amount":
        await query.edit_message_text("💵 Enter the new amount (number only):")
        return EDIT_AMOUNT
    elif query.data == "edit_category":
        categories = ['Food', 'Transportation', 'Entertainment', 'Services', 'Health', 'Shopping', 'Other']
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in categories]
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🏷️ Select the new category:", reply_markup=reply_markup)
        return EDIT_CATEGORY
    elif query.data == "edit_description":
        await query.edit_message_text("📋 Enter the new description:")
        return EDIT_DESCRIPTION
    elif query.data == "edit_date":
        await query.edit_message_text("📅 Enter the new date (e.g., 'today', 'yesterday', 'April 15'):")
        return EDIT_DATE

async def update_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_amount = float(update.message.text)
        expense_id = context.user_data.get('editing_id')
        
        supabase.table('expenses').update({'amount': new_amount}).eq('id', expense_id).execute()
        
        await update.message.reply_text(f"✅ Amount updated to ${new_amount:.2f}")
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return EDIT_AMOUNT
    except Exception as e:
        logger.error(f"Error updating amount: {e}")
        await update.message.reply_text("❌ Error updating.")
        return ConversationHandler.END

async def update_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    new_category = query.data.split("_")[1]
    expense_id = context.user_data.get('editing_id')
    
    try:
        supabase.table('expenses').update({'category': new_category}).eq('id', expense_id).execute()
        await query.edit_message_text(f"✅ Category updated to {new_category}")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        await query.edit_message_text("❌ Error updating.")
        return ConversationHandler.END

async def update_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_description = update.message.text
    expense_id = context.user_data.get('editing_id')
    
    try:
        supabase.table('expenses').update({'description': new_description}).eq('id', expense_id).execute()
        await update.message.reply_text(f"✅ Description updated")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error updating description: {e}")
        await update.message.reply_text("❌ Error updating.")
        return ConversationHandler.END

async def update_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    expense_id = context.user_data.get('editing_id')
    
    from dateutil import parser
    try:
        date_text_lower = date_text.lower()
        if date_text_lower in ['hoy', 'today']:
            parsed_date = datetime.now()
        elif date_text_lower in ['ayer', 'yesterday']:
            from datetime import timedelta
            parsed_date = datetime.now() - timedelta(days=1)
        else:
            parsed_date = parser.parse(date_text, fuzzy=True)
        
        date_iso = parsed_date.isoformat()
        supabase.table('expenses').update({'date': date_iso}).eq('id', expense_id).execute()
        
        await update.message.reply_text(f"✅ Date updated to {parsed_date.strftime('%Y-%m-%d')}")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error updating date: {e}")
        await update.message.reply_text("❌ Couldn't understand that date. Please try again.")
        return EDIT_DATE

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ Operation cancelled.")
    else:
        await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

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
        
        edit_handler = ConversationHandler(
            entry_points=[
                CommandHandler("edit", edit_command)
            ],
            states={
                0: [CallbackQueryHandler(select_transaction)],
                1: [CallbackQueryHandler(edit_field_selection)],
                EDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_amount)],
                EDIT_CATEGORY: [CallbackQueryHandler(update_category, pattern="^(cat_|cancel)")],
                EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_description)],
                EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_date)],
            },
            fallbacks=[CommandHandler("cancel", cancel_edit)]
        )
        
        app.add_handler(edit_handler)
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        logger.info("✅ Bot started successfully...")
        logger.info("🤖 Waiting for messages...")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()
