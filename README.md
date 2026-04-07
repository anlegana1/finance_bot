# 💰 Telegram Expense Tracker Bot

Intelligent Telegram bot that helps you track and categorize both expenses and income using artificial intelligence. Supports text input, receipt photos, and voice messages.

## 🌟 Features

- **Multiple input methods**:
  - 📝 Text: "Bought coffee for $5" or "Received salary of $1200"
  - 📸 Photo: Send a picture of your receipt
  - 🎤 Audio: Record a voice message
  
- **Automatic categorization** with ChatGPT (GPT-4)
- **Income and expense detection** in the same flow
- **Supabase database** for secure storage
- **Monthly summaries** with income, expenses, net balance, and categories
- **Voice recognition** with Whisper AI
- **Receipt OCR** with GPT-4 Vision

## 📋 Categories

The bot automatically categorizes your transactions into:
- 🍔 Food
- 🚗 Transportation
- 🎬 Entertainment
- 💡 Services
- 💊 Health
- 🛍️ Shopping
- 💼 Salary
- 🧑‍💻 Freelance
- 🏢 Business
- 📈 Investment
- 🎁 Gift
- 🔁 Refund
- 📦 Other

## 🚀 Installation

### 1. Clone or create the project

```bash
cd finance_bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file with your credentials:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token_here
OPENAI_API_KEY=your_openai_api_key_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

## 🔑 Getting Credentials

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy the token provided

### OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account or sign in
3. Go to "API Keys" and create a new key
4. **Important**: You need credits in your OpenAI account

### Supabase

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Go to "Settings" > "API"
4. Copy the project URL and the "anon/public" key
5. Go to "SQL Editor" and execute the `supabase_schema.sql` script

#### Run the schema in Supabase:

1. In your Supabase project, go to "SQL Editor"
2. Create a new query
3. Copy and paste the content of `supabase_schema.sql`
4. Execute the script (Run)
5. Verify that the `expenses` table has been created correctly
If you already created the previous version of the table, you must update it to include the new `transaction_type` field before running the bot again.

## ▶️ Usage

### Start the bot

```bash
python bot.py
```

### Available commands

- `/start` - Show welcome message
- `/summary` - View current month finance summary
- `/categories` - View list of available categories

### Usage examples

**Text entry:**
```
Bought coffee at Starbucks for $5.50
```

```
Received freelance payment of $350
```

**Photo entry:**
- Send a photo of the receipt or proof of payment
- The bot will automatically extract the amount, type, and description

**Voice entry:**
- Record a message: "Paid 20 dollars for Uber"
- Or: "I got a 500 dollar bonus"
- The bot will transcribe and process the transaction

## 📊 Project Structure

```
finance_bot/
├── bot.py                  # Main bot code
├── config.py               # Configuration management
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── supabase_schema.sql    # Database schema
├── .env                   # Environment variables (DO NOT commit to git)
├── .env.example           # Example environment variables
├── .gitignore            # Files to ignore in git
└── README.md             # This file
```

## 🗄️ Database Structure

### Table `expenses`

| Field | Type | Description |
|-------|------|-------------|
| id | BIGSERIAL | Unique ID |
| user_id | BIGINT | Telegram user ID |
| username | TEXT | Username |
| transaction_type | TEXT | `expense` or `income` |
| amount | DECIMAL(10,2) | Transaction amount |
| currency | TEXT | Fixed value: `CAD` |
| description | TEXT | Transaction description |
| category | TEXT | Transaction category |
| date | TIMESTAMP | Transaction date and time |
| created_at | TIMESTAMP | Record creation date |

## 🔒 Security

- Credentials are stored in `.env` (not committed to git)
- Supabase has Row Level Security (RLS) enabled
- Temporary files (photos, audio) are deleted after processing

## 💡 Important Notes

1. **Costs**: This bot uses paid APIs (OpenAI). Make sure you have sufficient credits
2. **Models used**:
   - GPT-4 for text categorization
   - GPT-4 Vision (gpt-4o) for image processing
   - Whisper for audio transcription
3. **Limits**: OpenAI has rate limits. For intensive use, consider implementing rate limiting

## 🐛 Troubleshooting

### Error: "Unauthorized"
- Verify that your `TELEGRAM_BOT_TOKEN` is correct
- Make sure the bot is active in BotFather

### Error: "Invalid API Key"
- Verify that your `OPENAI_API_KEY` is correct
- Make sure you have credits in your OpenAI account

### Error saving to Supabase
- Verify that you have executed the `supabase_schema.sql` script
- Check that the Supabase URL and KEY are correct
- Verify that the `expenses` table exists
- Verify that the table includes the `transaction_type` column

### Bot doesn't categorize well
- GPT-4 does its best. You can adjust the prompt in `bot.py`
- Consider using clearer descriptions for your transactions

## 🚀 Future Improvements

- [ ] Export transactions to Excel/CSV
- [ ] Separate income and expense reports
- [ ] Expense charts by category
- [ ] Spending limits per category
- [ ] Excessive spending notifications
- [ ] Multi-language support
- [ ] Web dashboard
- [ ] Edit and delete transactions

## 📝 License

This project is open source. Feel free to use and modify it.

## 🤝 Contributions

Contributions are welcome! If you find a bug or have a suggestion, open an issue.

---

**Happy expense tracking! 💰**
