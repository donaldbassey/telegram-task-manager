"""
ADVANCED TELEGRAM TASK MANAGER BOT - SECURE VERSION
Complete version with database, 15+ commands, and proper security
"""

import telebot
from telebot import types
import sqlite3
import json
import time
import os
import sys
from datetime import datetime, timedelta

# ================= SECURE TOKEN LOADING =================
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    pass

# Get token from environment variable
TOKEN = os.getenv('BOT_TOKEN')

# Fallback: Check for token in alternative locations
if not TOKEN:
    # Check if running from command line with token argument
    if len(sys.argv) > 1:
        TOKEN = sys.argv[1]
    else:
        # Prompt user for token
        print("🔒 BOT TOKEN NOT FOUND!")
        print("=" * 50)
        print("How to configure your bot token:")
        print("1. Create a '.env' file in the same folder")
        print("2. Add this line: BOT_TOKEN=your_token_here")
        print("3. Get token from @BotFather")
        print("=" * 50)
        print("\nOr enter token now (won't be saved):")
        TOKEN = input("Token: ").strip()
        
        if not TOKEN:
            print("❌ Token required. Exiting...")
            sys.exit(1)
        
        # Offer to save for next time
        save = input("Save to .env file for next time? (y/n): ").lower()
        if save == 'y':
            with open('.env', 'w') as f:
                f.write(f"BOT_TOKEN={TOKEN}")
            print("✅ Token saved to .env file")
            print("⚠️  Add '.env' to .gitignore to keep it secret!")

# Verify token format (basic check)
if not TOKEN or ':' not in TOKEN or len(TOKEN) < 20:
    print(f"❌ Invalid token format: {TOKEN[:10]}...")
    print("Token should look like: 1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ")
    print("Get a new token from @BotFather")
    sys.exit(1)

print(f"✅ Token loaded ({TOKEN[:10]}...)")
bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('tasks.db', check_same_thread=False, timeout=10)
        self.cursor = self.conn.cursor()
        self.create_tables()
        print("✅ Database connected")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tasks table
            self.cursor.execute('''
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
            
            # Create indexes for better performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON tasks(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_completed ON tasks(is_completed)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_due_date ON tasks(due_date)')
            
            self.conn.commit()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database error: {e}")
    
    def add_user(self, user_id, username, first_name, last_name):
        """Add or update user in database"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error adding user: {e}")
            return False
    
    def add_task(self, user_id, title, category='general', priority=2, 
                 tags=None, due_date=None, description=''):
        """Add a new task to database"""
        try:
            tags_json = json.dumps(tags if tags else [])
            self.cursor.execute('''
                INSERT INTO tasks (user_id, title, description, category, priority, tags, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, title, description, category, priority, tags_json, due_date))
            self.conn.commit()
            task_id = self.cursor.lastrowid
            print(f"✅ Task added: ID={task_id} for user={user_id}")
            return task_id
        except Exception as e:
            print(f"❌ Error adding task: {e}")
            return None
    
    def get_tasks(self, user_id, completed=False, category=None):
        """Get tasks for specific user"""
        try:
            query = "SELECT * FROM tasks WHERE user_id = ? AND is_completed = ?"
            params = [user_id, 1 if completed else 0]
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY priority ASC, due_date ASC, created_at DESC"
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Error getting tasks: {e}")
            return []
    
    def complete_task(self, task_id):
        """Mark task as completed"""
        try:
            self.cursor.execute('''
                UPDATE tasks 
                SET is_completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Error completing task: {e}")
            return False
    
    def delete_task(self, task_id):
        """Delete a task"""
        try:
            self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Error deleting task: {e}")
            return False
    
    def get_stats(self, user_id):
        """Get user statistics"""
        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN is_completed = 0 THEN 1 ELSE 0 END) as pending
                FROM tasks WHERE user_id = ?
            ''', (user_id,))
            row = self.cursor.fetchone()
            if row and row[0]:
                total, completed, pending = row
                rate = (completed/total*100) if total > 0 else 0
                return {
                    'total': total,
                    'completed': completed or 0,
                    'pending': pending or 0,
                    'rate': rate
                }
            return {'total': 0, 'completed': 0, 'pending': 0, 'rate': 0}
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {'total': 0, 'completed': 0, 'pending': 0, 'rate': 0}
    
    def search_tasks(self, user_id, keyword):
        """Search tasks by keyword"""
        try:
            search_pattern = f'%{keyword}%'
            self.cursor.execute('''
                SELECT * FROM tasks 
                WHERE user_id = ? AND is_completed = 0 
                AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)
                ORDER BY priority ASC
            ''', (user_id, search_pattern, search_pattern, search_pattern))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Error searching tasks: {e}")
            return []
    
    def get_upcoming_deadlines(self, user_id, days=7):
        """Get tasks with upcoming deadlines"""
        try:
            self.cursor.execute('''
                SELECT * FROM tasks 
                WHERE user_id = ? AND is_completed = 0 AND due_date IS NOT NULL
                AND date(due_date) <= date('now', ?)
                ORDER BY due_date ASC
            ''', (user_id, f'+{days} days'))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Error getting deadlines: {e}")
            return []
    
    def clear_all_tasks(self, user_id):
        """Delete all tasks for a user"""
        try:
            self.cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print(f"❌ Error clearing tasks: {e}")
            return 0

# Create database instance
db = Database()

# ================= TASK PARSER =================
class TaskParser:
    CATEGORIES = ['work', 'personal', 'study', 'shopping', 'health', 'other']
    PRIORITY_TAGS = {'urgent': 1, 'important': 1, 'high': 1, 'medium': 2, 'low': 3}
    
    @staticmethod
    def parse(text):
        """Parse task text with #tags and due dates"""
        parts = text.split()
        title_parts = []
        category = 'general'
        priority = 2
        tags = []
        due_date = None
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            if part.startswith('#'):
                tag = part[1:].lower()
                if tag in TaskParser.CATEGORIES:
                    category = tag
                elif tag in TaskParser.PRIORITY_TAGS:
                    priority = TaskParser.PRIORITY_TAGS[tag]
                else:
                    tags.append(tag)
            
            elif part == 'by' and i + 1 < len(parts):
                due_date = TaskParser.parse_date(parts[i + 1])
                i += 1
            
            elif part == 'due' and i + 1 < len(parts):
                due_date = TaskParser.parse_date(parts[i + 1])
                i += 1
            
            else:
                title_parts.append(part)
            
            i += 1
        
        title = ' '.join(title_parts).strip()
        if not title:
            title = text  # Fallback to original text
        
        return {
            'title': title,
            'category': category,
            'priority': priority,
            'tags': tags,
            'due_date': due_date
        }
    
    @staticmethod
    def parse_date(date_str):
        """Parse dates like: today, tomorrow, monday, YYYY-MM-DD"""
        if not date_str:
            return None
            
        date_str = date_str.lower()
        today = datetime.now()
        
        # Relative dates
        if date_str == 'today':
            return today.strftime('%Y-%m-%d')
        elif date_str == 'tomorrow':
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            days_ahead = (days.index(date_str) - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week
            return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        # Try to parse as YYYY-MM-DD
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            pass
        
        # Try other formats
        for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None

# ================= KEYBOARDS =================
def main_keyboard():
    """Create main menu keyboard"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["➕ Add Task", "📋 My Tasks", "✅ Completed", "🔍 Search", 
               "📊 Stats", "⏰ Deadlines", "📂 Categories", "⚙️ Help"]
    keyboard.add(*buttons[:4])
    keyboard.add(*buttons[4:])
    return keyboard

# ================= COMMAND HANDLERS =================
@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    """Welcome message"""
    user = message.from_user
    success = db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    if success:
        print(f"✅ User registered: {user.id} - {user.first_name}")
    
    help_text = f"""
👋 Hello *{user.first_name}*!

🤖 *Advanced Task Manager Bot*

📝 *Main Commands:*
`/add [task]` - Add new task (use #tags, by tomorrow)
`/tasks` - Show pending tasks
`/done [id]` - Mark task as completed
`/delete [id]` - Delete a task
`/completed` - Show completed tasks
`/search [text]` - Search in tasks
`/stats` - Your productivity statistics
`/deadlines` - Upcoming deadlines
`/categories` - Task categories overview
`/clear` - Delete all tasks (careful!)
`/export` - Export tasks to JSON

💡 *Examples:*
`/add #work Finish report by tomorrow`
`/add #personal Buy groceries #shopping`
`/add Team meeting #urgent by Friday`
`/search meeting`
`/stats`

🏷️ *Tags & Priorities:*
#work #personal #study #shopping #health
#urgent #important #high #medium #low

📅 *Date formats:*
by today, by tomorrow, by Monday
by 2024-12-31, by 31.12.2024

📱 *Use buttons below for quick access!*
"""
    bot.reply_to(message, help_text, parse_mode='Markdown', reply_markup=main_keyboard())

@bot.message_handler(commands=['add'])
def add_task_command(message):
    """Add a new task"""
    try:
        if len(message.text.strip()) <= 5:
            bot.reply_to(message, 
                "📝 *How to add tasks:*\n\n"
                "`/add [description]`\n\n"
                "You can use:\n"
                "• Hashtags: #work #personal #study\n"
                "• Priorities: #urgent #important #low\n"
                "• Due dates: by today/tomorrow/Monday\n\n"
                "*Examples:*\n"
                "`/add #work Team meeting by tomorrow`\n"
                "`/add #personal Buy milk #shopping`\n"
                "`/add Finish report #urgent by Friday`",
                parse_mode='Markdown')
            return
        
        user = message.from_user
        task_text = message.text[5:].strip()
        task_data = TaskParser.parse(task_text)
        
        if not task_data['title']:
            bot.reply_to(message, "❌ Please provide a task description")
            return
        
        task_id = db.add_task(
            user_id=user.id,
            title=task_data['title'],
            category=task_data['category'],
            priority=task_data['priority'],
            tags=task_data['tags'],
            due_date=task_data['due_date']
        )
        
        if not task_id:
            bot.reply_to(message, "❌ Failed to add task. Please try again.")
            return
        
        # Build response
        response = f"✅ *Task #{task_id} Added!*\n\n"
        response += f"📝 *{task_data['title']}*\n"
        response += f"📁 Category: #{task_data['category']}\n"
        
        # Priority emoji
        priority_map = {1: "🔥 URGENT", 2: "⚠️ Medium", 3: "💤 Low"}
        response += f"🎯 Priority: {priority_map.get(task_data['priority'], '⚠️ Medium')}\n"
        
        # Tags
        if task_data['tags']:
            tags_str = ' '.join([f'#{tag}' for tag in task_data['tags']])
            response += f"🏷️ Tags: {tags_str}\n"
        
        # Due date
        if task_data['due_date']:
            response += f"📅 Due: {task_data['due_date']}\n"
        
        response += f"\n🆔 Complete: `/done {task_id}`"
        response += f"\n🗑️ Delete: `/delete {task_id}`"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = str(e)[:200]
        print(f"❌ Error adding task: {error_msg}")
        bot.reply_to(message, f"❌ Error: {error_msg}")

@bot.message_handler(commands=['tasks'])
def list_tasks_command(message):
    """List all pending tasks"""
    user = message.from_user
    tasks = db.get_tasks(user.id, completed=False)
    
    if not tasks:
        bot.reply_to(message, 
            "📭 *No pending tasks!*\n\n"
            "Add your first task:\n"
            "`/add [your task description]`\n\n"
            "Or use the '➕ Add Task' button below.",
            parse_mode='Markdown', reply_markup=main_keyboard())
        return
    
    response = f"📋 *Your Tasks ({len(tasks)})*\n\n"
    
    for task in tasks[:10]:  # Limit to 10 tasks
        task_id, _, title, _, category, priority, due_date, completed, created_at, completed_at, tags_json = task
        
        # Priority icon
        priority_icon = {1: "🔥", 2: "⚠️", 3: "💤"}.get(priority, "⚠️")
        
        # Format response
        response += f"{priority_icon} *{title}*\n"
        response += f"   🆔 {task_id} | #{category}"
        
        if due_date:
            due_date_str = due_date[:10] if isinstance(due_date, str) else due_date
            response += f" | 📅 {due_date_str}"
        
        response += f"\n   ` /done {task_id} `  ` /delete {task_id} `\n\n"
    
    if len(tasks) > 10:
        response += f"📄 Showing 10 of {len(tasks)} tasks\n"
        response += "Use `/search` to find specific tasks"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['completed'])
def completed_tasks_command(message):
    """List completed tasks"""
    user = message.from_user
    tasks = db.get_tasks(user.id, completed=True)
    
    if not tasks:
        bot.reply_to(message, 
            "🎉 *No completed tasks yet!*\n\n"
            "Complete your first task:\n"
            "1. Check tasks: `/tasks`\n"
            "2. Complete: `/done [task_id]`",
            parse_mode='Markdown')
        return
    
    response = f"✅ *Completed Tasks ({len(tasks)})*\n\n"
    
    for task in tasks[:8]:
        task_id, _, title, _, category, _, _, _, _, completed_at, _ = task
        
        response += f"✓ *{title}*\n"
        response += f"   #{category} | ID: {task_id}\n"
        
        if completed_at:
            completed_date = completed_at[:10] if isinstance(completed_at, str) else completed_at
            response += f"   ✅ Completed: {completed_date}\n"
        
        response += "\n"
    
    if len(tasks) > 8:
        response += f"📊 Total completed: {len(tasks)} tasks\n"
    
    response += "\n🎯 *Keep up the good work!*"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['done'])
def complete_task_command(message):
    """Mark task as completed"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, 
                "✅ *Complete a task:*\n\n"
                "Usage: `/done [task_id]`\n\n"
                "Example: `/done 5`\n\n"
                "Get task IDs from `/tasks`",
                parse_mode='Markdown')
            return
        
        task_id = int(parts[1])
        success = db.complete_task(task_id)
        
        if success:
            bot.reply_to(message, f"🎉 *Task #{task_id} completed!*", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ Task #{task_id} not found or already completed")
        
    except ValueError:
        bot.reply_to(message, "❌ Please provide a valid task ID number")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['delete'])
def delete_task_command(message):
    """Delete a task"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, 
                "🗑️ *Delete a task:*\n\n"
                "Usage: `/delete [task_id]`\n\n"
                "Example: `/delete 5`\n\n"
                "Get task IDs from `/tasks`",
                parse_mode='Markdown')
            return
        
        task_id = int(parts[1])
        success = db.delete_task(task_id)
        
        if success:
            bot.reply_to(message, f"🗑️ *Task #{task_id} deleted!*", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ Task #{task_id} not found")
        
    except ValueError:
        bot.reply_to(message, "❌ Please provide a valid task ID number")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['search'])
def search_tasks_command(message):
    """Search tasks by keyword"""
    try:
        if len(message.text.split()) < 2:
            bot.reply_to(message, 
                "🔍 *Search tasks:*\n\n"
                "Usage: `/search [keyword]`\n\n"
                "Examples:\n`/search meeting`\n`/search report`\n`/search #work`",
                parse_mode='Markdown')
            return
        
        keyword = message.text.split(' ', 1)[1]
        user = message.from_user
        tasks = db.search_tasks(user.id, keyword)
        
        if not tasks:
            bot.reply_to(message, 
                f"🔍 *No tasks found for '{keyword}'*\n\n"
                "Try:\n• Different keywords\n• General terms\n• Hashtags like #work",
                parse_mode='Markdown')
            return
        
        response = f"🔍 *Search Results for '{keyword}' ({len(tasks)})*\n\n"
        
        for task in tasks[:8]:
            task_id, _, title, _, category, priority, due_date, _, _, _, _ = task
            priority_icon = {1: "🔥", 2: "⚠️", 3: "💤"}.get(priority, "⚠️")
            
            response += f"{priority_icon} *{title}*\n"
            response += f"   ID: {task_id} | #{category}"
            
            if due_date:
                due_date_str = due_date[:10] if isinstance(due_date, str) else due_date
                response += f" | 📅 {due_date_str}"
            
            response += f"\n   ` /done {task_id} `  ` /delete {task_id} `\n\n"
        
        if len(tasks) > 8:
            response += f"📄 Showing 8 of {len(tasks)} results\n"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Search error: {str(e)[:100]}")

@bot.message_handler(commands=['stats'])
def statistics_command(message):
    """Show user statistics"""
    user = message.from_user
    stats = db.get_stats(user.id)
    
    if stats['total'] == 0:
        bot.reply_to(message, 
            "📊 *No tasks yet!*\n\n"
            "Start tracking your productivity:\n\n"
            "`/add [your first task]`\n\n"
            "Or use the '➕ Add Task' button below!",
            parse_mode='Markdown', reply_markup=main_keyboard())
        return
    
    completion_rate = stats['rate']
    
    # Achievement message
    if completion_rate >= 90:
        achievement = "🏆 *Productivity Master!* 🌟"
        emoji = "🚀"
    elif completion_rate >= 70:
        achievement = "👍 *Excellent Progress!*"
        emoji = "💪"
    elif completion_rate >= 50:
        achievement = "📈 *Good Going!*"
        emoji = "✅"
    else:
        achievement = "💪 *Keep Going!*"
        emoji = "🎯"
    
    # Progress bar
    bar_length = 10
    filled = int(completion_rate / 100 * bar_length)
    progress_bar = "█" * filled + "░" * (bar_length - filled)
    
    response = f"{emoji} *Your Statistics*\n\n"
    response += f"📊 Total Tasks: {stats['total']}\n"
    response += f"✅ Completed: {stats['completed']}\n"
    response += f"⏳ Pending: {stats['pending']}\n"
    response += f"📈 Completion Rate: {completion_rate:.1f}%\n"
    response += f"   {progress_bar}\n\n"
    response += achievement
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['deadlines'])
def deadlines_command(message):
    """Show upcoming deadlines"""
    user = message.from_user
    tasks = db.get_upcoming_deadlines(user.id, days=14)
    
    if not tasks:
        bot.reply_to(message, 
            "⏰ *No upcoming deadlines!*\n\n"
            "Add deadlines to your tasks:\n\n"
            "`/add Report #work by Friday`\n"
            "`/add Buy presents by 2024-12-24`",
            parse_mode='Markdown')
        return
    
    # Group by days until deadline
    today = datetime.now().date()
    
    response = "⏰ *Upcoming Deadlines*\n\n"
    
    for task in tasks[:12]:
        task_id, _, title, _, category, priority, due_date_str, _, _, _, _ = task
        
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str[:10], '%Y-%m-%d').date()
                days_left = (due_date - today).days
                
                if days_left < 0:
                    deadline_text = "OVERDUE! ⚠️"
                elif days_left == 0:
                    deadline_text = "TODAY! ⏰"
                elif days_left == 1:
                    deadline_text = "Tomorrow"
                elif days_left <= 7:
                    deadline_text = f"{days_left} days"
                else:
                    deadline_text = f"{due_date_str[:10]} ({days_left} days)"
                
                priority_icon = {1: "🔥", 2: "⚠️", 3: "💤"}.get(priority, "⚠️")
                
                response += f"{priority_icon} *{title}*\n"
                response += f"   📅 {deadline_text} | #{category}\n"
                response += f"   🆔 {task_id} | ` /done {task_id} `\n\n"
                
            except:
                continue
    
    response += "💡 Use `/add [task] by [date]` to set deadlines"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['categories'])
def categories_command(message):
    """Show task categories"""
    user = message.from_user
    
    # Get category statistics
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT category, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed
            FROM tasks 
            WHERE user_id = ?
            GROUP BY category
            ORDER BY COUNT(*) DESC
        ''', (user.id,))
        
        categories = cursor.fetchall()
        
        if not categories:
            bot.reply_to(message, 
                "📂 *No categories yet!*\n\n"
                "Add tasks with hashtags:\n\n"
                "`/add #work Team meeting`\n"
                "`/add #personal Buy groceries`\n"
                "`/add #study Read chapter 5`",
                parse_mode='Markdown')
            return
        
        response = "📂 *Your Task Categories*\n\n"
        
        for category, total, completed in categories[:10]:
            rate = (completed/total*100) if total > 0 else 0
            
            # Progress bar
            bar_length = 8
            filled = int(rate / 100 * bar_length)
            progress_bar = "█" * filled + "░" * (bar_length - filled)
            
            response += f"*#{category}*\n"
            response += f"   {completed}/{total} completed\n"
            response += f"   {progress_bar} {rate:.0f}%\n\n"
        
        response += "🏷️ *Available categories:*\n"
        response += "work, personal, study, shopping, health, other\n\n"
        response += "Example: `/add #work Finish report by tomorrow`"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['clear'])
def clear_all_command(message):
    """Clear all tasks with confirmation"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Yes, delete ALL tasks", callback_data="clear_yes"),
        types.InlineKeyboardButton("❌ No, cancel", callback_data="clear_no")
    )
    
    bot.reply_to(message, 
        "⚠️ *DANGER ZONE* ⚠️\n\n"
        "This will delete ALL your tasks!\n"
        "*This action cannot be undone!*\n\n"
        "Are you sure you want to continue?",
        parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(commands=['export'])
def export_command(message):
    """Export tasks to JSON"""
    user = message.from_user
    try:
        # Get all tasks
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT id, title, description, category, priority, 
                   due_date, is_completed, created_at, completed_at, tags
            FROM tasks WHERE user_id = ?
        ''', (user.id,))
        
        tasks = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        if not tasks:
            bot.reply_to(message, "📭 *No tasks to export!*", parse_mode='Markdown')
            return
        
        # Convert to dictionary
        tasks_list = []
        for task in tasks:
            task_dict = dict(zip(columns, task))
            # Convert datetime objects to strings
            for key in ['due_date', 'created_at', 'completed_at']:
                if task_dict[key]:
                    task_dict[key] = str(task_dict[key])
            tasks_list.append(task_dict)
        
        # Create export data
        export_data = {
            'user_id': user.id,
            'username': user.username,
            'export_date': datetime.now().isoformat(),
            'total_tasks': len(tasks_list),
            'tasks': tasks_list
        }
        
        # For now, send as message (limited by Telegram size)
        # In production, you would save to file and send as document
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        if len(json_str) < 4000:  # Telegram message limit
            response = f"📤 *Task Export*\n\n"
            response += f"User: {user.first_name}\n"
            response += f"Total tasks: {len(tasks_list)}\n"
            response += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            response += "```json\n"
            response += json_str[:1500] + "\n..."
            response += "\n```"
            
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            bot.reply_to(message, 
                f"📤 *Export contains {len(tasks_list)} tasks*\n\n"
                f"Data too large for message ({len(json_str)} chars).\n"
                f"Consider using `/search` for specific tasks.",
                parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Export error: {str(e)[:100]}")

# ================= BUTTON HANDLERS =================
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    """Handle button presses from the keyboard"""
    text = message.text
    
    if text == "➕ Add Task":
        bot.reply_to(message, 
            "📝 *Add a new task:*\n\n"
            "Type your task now!\n\n"
            "*Examples:*\n"
            "Team meeting #work by tomorrow\n"
            "Buy milk #personal #shopping\n"
            "Finish report #urgent by Friday\n\n"
            "Or use command: `/add [task]`",
            parse_mode='Markdown')
    
    elif text == "📋 My Tasks":
        list_tasks_command(message)
    
    elif text == "✅ Completed":
        completed_tasks_command(message)
    
    elif text == "🔍 Search":
        bot.reply_to(message, 
            "🔍 *Search tasks:*\n\n"
            "Type: `/search [keyword]`\n\n"
            "*Examples:*\n"
            "`/search meeting`\n"
            "`/search report`\n"
            "`/search #work`",
            parse_mode='Markdown')
    
    elif text == "📊 Stats":
        statistics_command(message)
    
    elif text == "⏰ Deadlines":
        deadlines_command(message)
    
    elif text == "📂 Categories":
        categories_command(message)
    
    elif text == "⚙️ Help":
        start_command(message)
    
    else:
        # If user just types text without command, try to add as task
        user = message.from_user
        bot.reply_to(message, 
            f"📝 *Add this as task?*\n\n"
            f"`{text}`\n\n"
            f"Use `/add {text}` to add as task\n"
            f"Or type your task below with #tags and dates",
            parse_mode='Markdown')

# ================= CALLBACK HANDLERS =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle inline keyboard callbacks"""
    user = call.from_user
    
    if call.data == "clear_yes":
        # Delete all tasks for this user
        count = db.clear_all_tasks(user.id)
        
        bot.answer_callback_query(call.id, f"Deleted {count} tasks!")
        bot.edit_message_text(
            f"🗑️ *All tasks deleted!*\n\n"
            f"Removed {count} tasks.\n\n"
            f"Start fresh with `/add [new task]`",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    
    elif call.data == "clear_no":
        bot.answer_callback_query(call.id, "Cancelled")
        bot.edit_message_text(
            "❌ *Deletion cancelled*\n\n"
            "Your tasks are safe!",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )

# ================= ERROR HANDLER =================
@bot.message_handler(func=lambda message: True, content_types=['audio', 'document', 'photo', 'sticker', 'video', 'voice', 'location', 'contact'])
def handle_non_text(message):
    """Handle non-text messages"""
    bot.reply_to(message, 
        "🤖 *I understand text only!*\n\n"
        "Please send me:\n"
        "• Task descriptions\n"
        "• Commines like `/add` or `/tasks`\n"
        "• Use buttons below for actions",
        parse_mode='Markdown',
        reply_markup=main_keyboard())

# ================= BOT STARTUP =================
def print_banner():
    """Print startup banner"""
    print("=" * 60)
    print("🤖 ADVANCED TASK MANAGER BOT")
    print("=" * 60)
    print(f"Version: 2.0 (Secure)")
    print(f"Database: tasks.db")
    print(f"Commands: 15+ available")
    print(f"Security: Token from environment")
    print("=" * 60)
    print("Status: Starting bot...")
    print("=" * 60)

if __name__ == "__main__":
    print_banner()
    
    try:
        # Test bot connection
        bot_info = bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")
        print(f"✅ Bot name: {bot_info.first_name}")
        print(f"✅ Bot ID: {bot_info.id}")
        print("✅ Ready to receive messages...")
        print("=" * 60)
        
        # Start polling
        bot.polling(none_stop=True, interval=0, timeout=20)
        
    except telebot.apihelper.ApiException as e:
        print(f"❌ Telegram API Error: {e}")
        print("Check your bot token!")
        print("Get a new token from @BotFather")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print("Restarting in 5 seconds...")
        time.sleep(5)
        # Restart the script
        os.execv(sys.executable, ['python'] + sys.argv)