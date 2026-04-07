import os
import sys
import subprocess

def print_step(step_num, message):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {message}")
    print('='*60)

def main():
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║    Telegram Expense Tracker Bot - Setup              ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    print_step(1, "Verifying Python")
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    print_step(2, "Installing dependencies")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Error installing dependencies")
        return
    
    print_step(3, "Verifying .env file")
    if not os.path.exists('.env'):
        print("⚠️  .env file not found")
        print("📝 Creating .env from .env.example...")
        try:
            with open('.env.example', 'r') as example, open('.env', 'w') as env:
                env.write(example.read())
            print("✅ .env file created")
            print("\n⚠️  IMPORTANT: You must edit .env with your credentials before continuing")
            print("   1. TELEGRAM_BOT_TOKEN (get from @BotFather)")
            print("   2. OPENAI_API_KEY (get from platform.openai.com)")
            print("   3. SUPABASE_URL and SUPABASE_KEY (get from supabase.com)")
        except Exception as e:
            print(f"❌ Error creating .env: {e}")
            return
    else:
        print("✅ .env file found")
    
    print_step(4, "Verifying configuration")
    try:
        from config import Config
        Config.validate()
        print("✅ Valid configuration")
    except ValueError as e:
        print(f"❌ {e}")
        print("\n📝 Please edit the .env file with your credentials")
        return
    except Exception as e:
        print(f"❌ Error validating configuration: {e}")
        return
    
    print_step(5, "Setup complete!")
    print("""
    ✅ The bot is ready to run!
    
    📋 Next steps:
    
    1. Execute the SQL script in Supabase:
       - Open your project at supabase.com
       - Go to SQL Editor
       - Copy and paste the content of supabase_schema.sql
       - Execute the script
    
    2. Start the bot:
       python bot.py
    
    3. Open Telegram and send /start to your bot
    
    📚 For more information, check README.md
    """)

if __name__ == "__main__":
    main()
