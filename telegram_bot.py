import sqlite3
import random
import os
import requests
import psycopg2
from datetime import date, datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread
import pytz


TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = "bible.db"
RENDER_URL = "https://bible-bot-khj6.onrender.com"

TIMEZONE_OPTIONS = {
    "1": ("🇬🇧 UK (London)", "Europe/London"),
    "2": ("🇺🇸 US Eastern (New York)", "America/New_York"),
    "3": ("🇺🇸 US Central (Chicago)", "America/Chicago"),
    "4": ("🇺🇸 US Pacific (Los Angeles)", "America/Los_Angeles"),
    "5": ("🇳🇬 Nigeria (Lagos)", "Africa/Lagos"),
    "6": ("🇮🇳 India (Mumbai)", "Asia/Kolkata"),
    "7": ("🇦🇺 Australia (Sydney)", "Australia/Sydney"),
    "8": ("🇿🇦 South Africa (Johannesburg)", "Africa/Johannesburg"),
    "9": ("🇰🇪 Kenya (Nairobi)", "Africa/Nairobi"),
    "10": ("🇬🇭 Ghana (Accra)", "Africa/Accra"),
    "11": ("🇨🇦 Canada (Toronto)", "America/Toronto"),
    "12": ("🇩🇪 Germany (Berlin)", "Europe/Berlin"),
    "13": ("🇫🇷 France (Paris)", "Europe/Paris"),
    "14": ("🇧🇷 Brazil (Sao Paulo)", "America/Sao_Paulo"),
    "15": ("🇵🇭 Philippines (Manila)", "Asia/Manila"),
}

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bible Bot is running!"

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


# ============================================
# POSTGRESQL - SUBSCRIBERS (PERSISTENT)
# ============================================

def get_pg_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(DATABASE_URL)


def setup_subscribers_table():
    """Create subscribers table in PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_date TEXT,
            timezone TEXT DEFAULT 'UTC'
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ PostgreSQL subscribers table ready", flush=True)


def add_subscriber(chat_id, username=None, first_name=None, timezone='UTC'):
    """Add subscriber to PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO subscribers (chat_id, username, first_name, subscribed_date, timezone)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                timezone = EXCLUDED.timezone
        ''', (chat_id, username, first_name, date.today().isoformat(), timezone))
        conn.commit()
        success = True
        print(f"✅ Added subscriber: {chat_id} TZ: {timezone}", flush=True)
    except Exception as e:
        print(f"❌ Error adding subscriber: {e}", flush=True)
        success = False
    conn.close()
    return success


def update_subscriber_timezone(chat_id, timezone):
    """Update subscriber timezone in PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE subscribers SET timezone = %s WHERE chat_id = %s', (timezone, chat_id))
    conn.commit()
    rows_updated = cursor.rowcount
    conn.close()
    return rows_updated > 0


def get_subscriber_timezone(chat_id):
    """Get subscriber timezone from PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT timezone FROM subscribers WHERE chat_id = %s', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def remove_subscriber(chat_id):
    """Remove subscriber from PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscribers WHERE chat_id = %s', (chat_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0


def is_subscribed(chat_id):
    """Check if subscribed in PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM subscribers WHERE chat_id = %s', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_all_subscribers():
    """Get all subscribers from PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, timezone FROM subscribers')
    results = cursor.fetchall()
    conn.close()
    return results


def get_subscriber_count():
    """Get subscriber count from PostgreSQL"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM subscribers')
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ============================================
# SQLITE - BIBLE VERSES (READ ONLY)
# ============================================

def search_bible(keyword, limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE v.text LIKE ?
        LIMIT ?
    '''
    cursor.execute(query, (f'%{keyword}%', limit))
    results = cursor.fetchall()
    conn.close()
    return results


def get_random_verse():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        ORDER BY RANDOM()
        LIMIT 1
    '''
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result


def get_specific_verse(book_name, chapter, verse):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ? AND v.chapter = ? AND v.verse = ?
    '''
    cursor.execute(query, (f'%{book_name}%', chapter, verse))
    result = cursor.fetchone()
    conn.close()
    return result


def get_chapter(book_name, chapter):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ? AND v.chapter = ?
        ORDER BY v.verse
    '''
    cursor.execute(query, (f'%{book_name}%', chapter))
    results = cursor.fetchall()
    conn.close()
    return results


def search_by_book(book_name, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ?
        LIMIT ?
    '''
    cursor.execute(query, (f'%{book_name}%', limit))
    results = cursor.fetchall()
    conn.close()
    return results


def get_all_books():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT book_name, testament FROM books ORDER BY book_id")
    results = cursor.fetchall()
    conn.close()
    return results


def get_verse_of_the_day():
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.testament = 'New'
    ''')
    total = cursor.fetchone()[0]
    if total == 0:
        cursor.execute("SELECT COUNT(*) FROM verses")
        total = cursor.fetchone()[0]
        random.seed(seed)
        verse_id = random.randint(1, total)
        query = '''
            SELECT b.book_name, v.chapter, v.verse, v.text
            FROM verses v
            JOIN books b ON v.book_id = b.book_id
            WHERE v.id = ?
        '''
        cursor.execute(query, (verse_id,))
    else:
        random.seed(seed)
        offset = random.randint(0, total - 1)
        query = '''
            SELECT b.book_name, v.chapter, v.verse, v.text
            FROM verses v
            JOIN books b ON v.book_id = b.book_id
            WHERE b.testament = 'New'
            LIMIT 1 OFFSET ?
        '''
        cursor.execute(query, (offset,))
    result = cursor.fetchone()
    conn.close()
    return result


def get_all_topics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT topic_name FROM topics ORDER BY topic_name")
    results = cursor.fetchall()
    conn.close()
    return [r[0] for r in results]


def get_verses_by_topic(topic_name, limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = '''
        SELECT b.book_name, t.chapter, t.verse, v.text
        FROM topics t
        JOIN books b ON t.book_id = b.book_id
        JOIN verses v ON t.book_id = v.book_id AND t.chapter = v.chapter AND t.verse = v.verse
        WHERE t.topic_name = ?
        LIMIT ?
    '''
    cursor.execute(query, (topic_name.lower(), limit))
    results = cursor.fetchall()
    conn.close()
    return results


# ============================================
# BOT COMMANDS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed = is_subscribed(chat_id)
    if subscribed:
        tz = get_subscriber_timezone(chat_id)
        sub_status = f"✅ Subscribed (Timezone: {tz})"
    else:
        sub_status = "❌ Not subscribed yet"
    welcome = f"""
🙏 *Welcome to Bible Bot!*

{sub_status}

*📚 Commands:*

/search <word> - Search for verses
/verse John 3:16 - Get specific verse
/chapter Psalm 23 - Get full chapter
/book Romans - Browse a book
/books - List all 66 books
/topic <topic> - Search by topic
/topics - List all topics
/votd - Verse of the Day
/random - Random verse
/subscribe - Get daily verses at 6 AM
/unsubscribe - Stop daily verses
/settimezone - Set your timezone
/mystatus - Check subscription
/testdaily - Test daily verse
/help - Show all commands
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *Bible Bot Help*

*🔍 Search:*
/search <word> - Search verses
/topic <topic> - Search by topic
/topics - See all topics

*📍 Get Verses:*
/verse John 3:16
/chapter Psalm 23
/book Romans
/books - List all books

*🌅 Daily Verses:*
/votd - Verse of the Day
/random - Random verse
/subscribe - Daily verse at 6 AM
/unsubscribe - Stop daily verses
/settimezone - Set timezone
/mystatus - Check subscription
/testdaily - Test daily verse
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def settimezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.args:
        choice = context.args[0]
        if choice in TIMEZONE_OPTIONS:
            tz_name, tz_value = TIMEZONE_OPTIONS[choice]
            if is_subscribed(chat_id):
                update_subscriber_timezone(chat_id, tz_value)
                await update.message.reply_text(
                    f"✅ *Timezone updated!*\n\n"
                    f"🌍 {tz_name}\n"
                    f"⏰ Daily verses at 6:00 AM your local time!",
                    parse_mode='Markdown'
                )
            else:
                context.user_data['timezone'] = tz_value
                await update.message.reply_text(
                    f"✅ *Timezone set!*\n\n"
                    f"🌍 {tz_name}\n\n"
                    f"Now use /subscribe to receive daily verses!",
                    parse_mode='Markdown'
                )
            return
    response = "🌍 *Select Your Timezone*\n\n"
    for key, (name, _) in TIMEZONE_OPTIONS.items():
        response += f"{key}. {name}\n"
    response += "\n*Example:* /settimezone 1"
    await update.message.reply_text(response, parse_mode='Markdown')


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    username = user.username if user else None
    first_name = user.first_name if user else None
    if is_subscribed(chat_id):
        tz = get_subscriber_timezone(chat_id)
        await update.message.reply_text(
            f"✅ You're already subscribed!\n\n"
            f"🌍 Timezone: {tz}\n"
            f"⏰ Daily verse at 6:00 AM\n\n"
            f"/settimezone - Change timezone\n"
            f"/unsubscribe - Stop daily verses"
        )
        return
    timezone = context.user_data.get('timezone', None)
    if not timezone:
        response = "🌍 *Set your timezone first!*\n\n"
        for key, (name, _) in TIMEZONE_OPTIONS.items():
            response += f"{key}. {name}\n"
        response += "\n*Example:* /settimezone 1\n\nThen /subscribe again!"
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    if add_subscriber(chat_id, username, first_name, timezone):
        total = get_subscriber_count()
        tz_display = timezone
        for key, (name, value) in TIMEZONE_OPTIONS.items():
            if value == timezone:
                tz_display = name
                break
        await update.message.reply_text(
            f"🎉 *Successfully subscribed!*\n\n"
            f"🌍 {tz_display}\n"
            f"⏰ Daily verse at 6:00 AM your time!\n"
            f"👥 Total subscribers: {total}\n\n"
            f"/votd - Get today's verse now!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to subscribe. Try again.")


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_subscribed(chat_id):
        await update.message.reply_text("ℹ️ You're not subscribed.\n\nUse /subscribe to start!")
        return
    if remove_subscriber(chat_id):
        await update.message.reply_text(
            "👋 *Unsubscribed*\n\nUse /subscribe to start again!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed. Try again.")


async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if is_subscribed(chat_id):
        total = get_subscriber_count()
        tz = get_subscriber_timezone(chat_id)
        tz_display = tz
        for key, (name, value) in TIMEZONE_OPTIONS.items():
            if value == tz:
                tz_display = name
                break
        try:
            user_tz = pytz.timezone(tz)
            user_time = datetime.now(user_tz)
            time_str = user_time.strftime('%H:%M:%S')
        except:
            time_str = "Unknown"
        response = (
            f"✅ *You are subscribed!*\n\n"
            f"🌍 Timezone: {tz_display}\n"
            f"🕐 Your current time: {time_str}\n"
            f"⏰ Daily verse: 6:00 AM\n"
            f"👥 Total subscribers: {total}\n"
            f"💾 Data stored in: PostgreSQL (persistent)"
        )
    else:
        response = "❌ *Not subscribed*\n\n/settimezone then /subscribe"
    await update.message.reply_text(response, parse_mode='Markdown')


async def testdaily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_subscribed(chat_id):
        await update.message.reply_text("❌ Not subscribed. Use /subscribe first.")
        return
    tz_str = get_subscriber_timezone(chat_id)
    try:
        tz = pytz.timezone(tz_str) if tz_str else pytz.UTC
        user_time = datetime.now(tz)
    except:
        tz = pytz.UTC
        user_time = datetime.now(tz)
    await update.message.reply_text(
        f"🔍 *Debug Info:*\n\n"
        f"📍 Timezone: `{tz_str}`\n"
        f"🕐 Your time: `{user_time.strftime('%H:%M:%S')}`\n"
        f"📅 Date: `{user_time.strftime('%Y-%m-%d')}`\n"
        f"💾 Database: PostgreSQL (persistent)\n\n"
        f"Sending test verse...",
        parse_mode='Markdown'
    )
    verse = get_verse_of_the_day()
    if verse:
        book, chapter, verse_num, text = verse
        today = date.today().strftime("%B %d, %Y")
        message = f"🌅 *Test Daily Verse*\n📅 _{today}_\n\n📖 *{book} {chapter}:{verse_num}*\n\n_{text}_\n\n🙏 Have a blessed day!"
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Could not get verse.")


async def votd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_verse_of_the_day()
    if verse:
        book, chapter, verse_num, text = verse
        today = date.today().strftime("%B %d, %Y")
        response = f"🌅 *Verse of the Day*\n📅 _{today}_\n\n📖 *{book} {chapter}:{verse_num}*\n\n_{text}_\n\n🙏 Have a blessed day!"
    else:
        response = "❌ Could not get verse."
    await update.message.reply_text(response, parse_mode='Markdown')


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_random_verse()
    if verse:
        book, chapter, verse_num, text = verse
        response = f"🎲 *Random Verse*\n\n📖 *{book} {chapter}:{verse_num}*\n\n_{text}_"
    else:
        response = "❌ Could not get verse."
    await update.message.reply_text(response, parse_mode='Markdown')


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /search love")
        return
    keyword = ' '.join(context.args)
    results = search_bible(keyword)
    if not results:
        await update.message.reply_text(f"❌ No verses for '{keyword}'")
        return
    response = f"🔍 *Found {len(results)} verse(s):*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = get_all_topics()
    response = "📚 *Topics:*\n\n"
    for i, topic in enumerate(topics, 1):
        response += f"{i}. {topic.title()}\n"
    response += "\n*Example:* /topic salvation"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /topic salvation")
        return
    topic_name = ' '.join(context.args).lower()
    results = get_verses_by_topic(topic_name)
    if not results:
        await update.message.reply_text(f"❌ Topic '{topic_name}' not found. Use /topics")
        return
    response = f"📚 *{topic_name.title()}*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /verse John 3:16")
        return
    text = ' '.join(context.args)
    try:
        if ':' not in text:
            await update.message.reply_text("Format: /verse Book Chapter:Verse")
            return
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]
        chapter, verse = chapter_verse.split(':')
        chapter = int(chapter)
        verse = int(verse)
    except:
        await update.message.reply_text("Format: /verse Book Chapter:Verse")
        return
    result = get_specific_verse(book_name, chapter, verse)
    if result:
        book, chap, ver, txt = result
        response = f"📖 *{book} {chap}:{ver}*\n\n_{txt}_"
    else:
        response = f"❌ Not found: {book_name} {chapter}:{verse}"
    await update.message.reply_text(response, parse_mode='Markdown')


async def chapter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /chapter Psalm 23")
        return
    text = ' '.join(context.args)
    try:
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter = int(parts[1])
    except:
        await update.message.reply_text("Format: /chapter Book Chapter")
        return
    results = get_chapter(book_name, chapter)
    if not results:
        await update.message.reply_text(f"❌ Not found: {book_name} {chapter}")
        return
    response = f"📖 *{book_name.title()} {chapter}*\n\n"
    for verse_num, txt in results[:30]:
        response += f"*{verse_num}.* {txt}\n\n"
    if len(results) > 30:
        response += f"_(30 of {len(results)})_"
    await update.message.reply_text(response, parse_mode='Markdown')


async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /book John")
        return
    book_name = ' '.join(context.args)
    results = search_by_book(book_name)
    if not results:
        await update.message.reply_text(f"❌ Not found: {book_name}")
        return
    response = f"📚 *{book_name.title()}*\n\n"
    for book, chapter, verse, txt in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{txt}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    books = get_all_books()
    old = [b[0] for b in books if b[1] == "Old"]
    new = [b[0] for b in books if b[1] == "New"]
    response = "📚 *Bible Books*\n\n*Old Testament (39):*\n"
    response += ", ".join(old[:20]) + "\n" + ", ".join(old[20:]) + "\n\n"
    response += "*New Testament (27):*\n" + ", ".join(new)
    await update.message.reply_text(response, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if not keyword:
        return
    results = search_bible(keyword)
    if not results:
        await update.message.reply_text(f"❌ No verses for '{keyword}'")
        return
    response = f"🔍 *Found {len(results)} verse(s):*\n\n"
    for book, chapter, verse, txt in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{txt}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


# ============================================
# DAILY VERSE AUTO-SEND
# ============================================

async def check_and_send_daily_verses(context: ContextTypes.DEFAULT_TYPE):
    current_utc = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    print(f"⏰ Hourly check at {current_utc} UTC", flush=True)

    # Self-ping to stay awake
    try:
        requests.get(f"{RENDER_URL}/health", timeout=10)
        print("🏓 Self-ping OK", flush=True)
    except Exception as e:
        print(f"🏓 Self-ping failed: {e}", flush=True)

    # Get all subscribers from PostgreSQL
    subscribers = get_all_subscribers()

    if not subscribers:
        print("📭 No subscribers", flush=True)
        return

    print(f"👥 Checking {len(subscribers)} subscribers...", flush=True)

    verse = get_verse_of_the_day()
    if not verse:
        print("❌ Could not get verse", flush=True)
        return

    book, chapter, verse_num, text = verse
    today = date.today().strftime("%B %d, %Y")

    message = f"🌅 *Good Morning! Daily Verse*\n"
    message += f"📅 _{today}_\n\n"
    message += f"📖 *{book} {chapter}:{verse_num}*\n\n"
    message += f"_{text}_\n\n"
    message += "🙏 Have a blessed day!\n\n"
    message += "_/unsubscribe to stop_"

    sent_count = 0

    for chat_id, timezone_str in subscribers:
        try:
            if not timezone_str:
                timezone_str = 'UTC'

            tz = pytz.timezone(timezone_str)
            user_time = datetime.now(tz)

            print(f"  👤 {chat_id}: TZ={timezone_str}, Time={user_time.strftime('%H:%M')}", flush=True)

            if user_time.hour == 6:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                sent_count += 1
                print(f"  ✅ Sent to {chat_id}", flush=True)

        except Exception as e:
            print(f"  ❌ Error {chat_id}: {e}", flush=True)
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                remove_subscriber(chat_id)
                print(f"  🗑️ Removed {chat_id}", flush=True)

    print(f"📤 Done: {sent_count} sent", flush=True)


# ============================================
# MAIN
# ============================================

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN not set!", flush=True)
        return

    if not DATABASE_URL:
        print("❌ DATABASE_URL not set!", flush=True)
        return

    print("=" * 50, flush=True)
    print("🤖 Starting Bible Bot...", flush=True)
    print("=" * 50, flush=True)

    # Setup PostgreSQL subscribers table
    setup_subscribers_table()

    # Start Flask for keep-alive
    keep_alive()

    # Create bot
    bot_app = Application.builder().token(TOKEN).build()

    # Commands
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("votd", votd_command))
    bot_app.add_handler(CommandHandler("random", random_command))
    bot_app.add_handler(CommandHandler("search", search_command))
    bot_app.add_handler(CommandHandler("topics", topics_command))
    bot_app.add_handler(CommandHandler("topic", topic_command))
    bot_app.add_handler(CommandHandler("verse", verse_command))
    bot_app.add_handler(CommandHandler("chapter", chapter_command))
    bot_app.add_handler(CommandHandler("book", book_command))
    bot_app.add_handler(CommandHandler("books", books_command))
    bot_app.add_handler(CommandHandler("subscribe", subscribe_command))
    bot_app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    bot_app.add_handler(CommandHandler("mystatus", mystatus_command))
    bot_app.add_handler(CommandHandler("settimezone", settimezone_command))
    bot_app.add_handler(CommandHandler("testdaily", testdaily_command))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Hourly job
    job_queue = bot_app.job_queue
    job_queue.run_repeating(
        check_and_send_daily_verses,
        interval=3600,
        first=10
    )
    print("📅 Hourly check scheduled", flush=True)

    count = get_subscriber_count()
    print(f"👥 Subscribers: {count}", flush=True)
    print("💾 Using PostgreSQL for subscribers", flush=True)
    print("📖 Using SQLite for Bible verses", flush=True)
    print("✅ Bot is running!", flush=True)

    bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
