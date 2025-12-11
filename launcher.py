"""
TELEGRAM TASK MANAGER BOT - AUTOMATIC LAUNCHER
Run this file to install everything and start the bot
"""

import os
import sys
import subprocess
import time
import sqlite3

def print_header():
    print("═" * 60)
    print("🤖 ADVANCED TELEGRAM TASK MANAGER BOT")
    print("═" * 60)

def setup_environment():
    """Install all required packages"""
    print("\n[1/4] SETTING UP ENVIRONMENT...")
    
    packages = [
        "pyTelegramBotAPI==4.14.0",
        "python-dotenv==1.0.0"
    ]
    
    for package in packages:
        print(f"  Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✓ {package.split('==')[0]} installed")
        except subprocess.CalledProcessError:
            print(f"  ⚠️  Could not install {package}")
            print(f"  Try: pip install {package}")
    
    print("  ✓ Environment ready")

def setup_database():
    """Create and initialize SQLite database"""
    print("\n[2/4] SETTING UP DATABASE...")
    
    try:
        # Create tasks.db with all tables
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'general',
                priority INTEGER DEFAULT 2,
                due_date TIMESTAMP,
                is_completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                tags TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # User settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                daily_reminder BOOLEAN DEFAULT 0,
                reminder_time TEXT DEFAULT '09:00',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("  ✓ Database 'tasks.db' created")
        print("  ✓ Tables: users, tasks, user_settings")
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def check_configuration():
    """Check if bot token is configured"""
    print("\n[3/4] CHECKING CONFIGURATION...")
    
    # Check if bot.py exists
    if not os.path.exists('bot.py'):
        print("  ❌ bot.py not found")
        return False
    
    # Read bot.py to check token
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for placeholder token
    if "YOUR_BOT_TOKEN_HERE" in content or "PASTE_YOUR_TOKEN" in content:
        print("  ⚠️  WARNING: Bot token not configured!")
        print("\n" + "═" * 50)
        print("⚙️  CONFIGURATION REQUIRED")
        print("═" * 50)
        print("\n1. Open Telegram and find @BotFather")
        print("2. Send: /newbot")
        print("3. Choose bot name and username")
        print("4. COPY the token (looks like: 123456:ABCdef...)")
        print("\n5. Edit bot.py file")
        print("6. Find line: TOKEN = \"YOUR_TOKEN_HERE\"")
        print("7. Replace with: TOKEN = \"your_actual_token_here\"")
        print("\nExample: TOKEN = \"1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ\"")
        print("═" * 50)
        
        response = input("\nOpen bot.py to edit now? (y/n): ")
        if response.lower() == 'y':
            try:
                os.system("notepad bot.py")
                print("\nPlease save the file and restart.")
                input("Press Enter after saving...")
            except:
                print("Please open bot.py manually in a text editor")
        
        return False
    
    print("  ✓ Bot token configured")
    return True

def start_bot():
    """Start the Telegram bot"""
    print("\n[4/4] STARTING BOT...")
    print("\n" + "═" * 60)
    print("🚀 BOT IS NOW STARTING")
    print("═" * 60)
    print("\n📱 INSTRUCTIONS:")
    print("1. Keep this window OPEN")
    print("2. Open Telegram on your phone/computer")
    print("3. Search for your bot username")
    print("4. Click START button")
    print("5. Try: /add Buy milk")
    print("6. Try: /tasks")
    print("\n⚠️  Press CTRL+C to stop the bot")
    print("═" * 60 + "\n")
    
    # Wait a moment
    time.sleep(2)
    
    try:
        # Import and run bot
        import bot
        print("\nBot stopped. Restarting...")
        time.sleep(3)
        os.execv(sys.executable, ['python'] + sys.argv)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
        print("To restart, run: python launcher.py")
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure all files are in the same folder:")
        print("  - bot.py, database.py, task_manager.py, launcher.py")
    except Exception as e:
        print(f"\n❌ Bot error: {str(e)}")
        print("Restarting in 5 seconds...")
        time.sleep(5)
        start_bot()

def main():
    """Main launcher function"""
    print_header()
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        print(f"Current: Python {sys.version_info.major}.{sys.version_info.minor}")
        input("\nPress Enter to exit...")
        return
    
    # Setup steps
    setup_environment()
    
    if not setup_database():
        print("⚠️  Database setup had issues, but continuing...")
    
    if not check_configuration():
        print("\n⚠️  Configuration incomplete")
        response = input("Start bot anyway? (y/n): ")
        if response.lower() != 'y':
            print("\nExiting...")
            input("Press Enter to close...")
            return
    
    # Start the bot
    start_bot()

if __name__ == "__main__":
    main()