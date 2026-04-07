from config import Config

def test_configuration():
    print("🔍 Verifying configuration...\n")
    
    try:
        Config.validate()
        print("✅ All environment variables are configured correctly\n")
        
        print("📋 Current configuration:")
        print(f"  Telegram Bot Token: {'*' * 20}{Config.TELEGRAM_BOT_TOKEN[-10:] if Config.TELEGRAM_BOT_TOKEN else 'NOT CONFIGURED'}")
        print(f"  OpenAI API Key: {'*' * 20}{Config.OPENAI_API_KEY[-10:] if Config.OPENAI_API_KEY else 'NOT CONFIGURED'}")
        print(f"  Supabase URL: {Config.SUPABASE_URL[:30]}..." if Config.SUPABASE_URL else "NOT CONFIGURED")
        print(f"  Supabase Key: {'*' * 20}{Config.SUPABASE_KEY[-10:] if Config.SUPABASE_KEY else 'NOT CONFIGURED'}")
        print(f"\n📂 Available categories: {', '.join(Config.CATEGORIES)}")
        print("\n✅ The bot is ready to run!")
        print("👉 Execute: python bot.py")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\n📝 Steps to configure:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env with your credentials")
        print("3. Run this script again")
        return False
    
    return True

if __name__ == "__main__":
    test_configuration()
