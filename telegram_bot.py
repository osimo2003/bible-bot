import sqlite3
import random
import os
from datetime import date, time, datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread
import pytz


TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = "bible.db"

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

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


def setup_subscribers_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_date TEXT,
            timezone TEXT DEFAULT 'UTC'
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Subscribers table ready", flush=True)


def add_subscriber(chat_id, username=None, first_name=None, timezone='UTC'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO subscribers (chat_id, username, first_name, subscribed_date, timezone)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, username, first_name, date.today().isoformat(), timezone))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error adding subscriber: {e}", flush=True)
        success = False
    conn.close()
    return success


def update_subscriber_timezone(chat_id, timezone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE subscribers SET timezone = ? WHERE chat_id = ?', (timezone, chat_id))
    conn.commit()
    rows_updated = cursor.rowcount
    conn.close()
    return rows_updated > 0


def get_subscriber_timezone(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timezone FROM subscribers WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def remove_subscriber(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0


def is_subscribed(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM subscribers WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, timezone FROM subscribers')
    results = cursor.fetchall()
    conn.close()
    return results


def get_subscriber_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM subscribers')
    count = cursor.fetchone()[0]
    conn.close()
    return count


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
    
    # Get only New Testament verses
    cursor.execute('''
        SELECT COUNT(*) FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.testament = 'New'
    ''')
    total = cursor.fetchone()[0]
    
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

*Search:*
/search <word> - Search for verses
/topic <topic> - Search by topic
/topics - List all topics

*Get Verses:*
/verse John 3:16 - Get specific verse
/chapter Psalm 23 - Get full chapter
/book Romans - Browse a book
/books - List all 66 books

*Daily:*
/votd - Verse of the Day
/random - Random verse
/subscribe - Get daily verses at 6 AM
/unsubscribe - Stop daily verses
/settimezone - Set your timezone
/mystatus - Check subscription

/help - Show all commands
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *Bible Bot Help*

*🔍 Search Commands:*
/search <word> - Search all verses
/topic <topic> - Search by topic
/topics - See all topics

*📍 Get Specific Verses:*
/verse John 3:16
/verse Genesis 1:1

*📄 Get Chapters:*
/chapter John 3
/chapter Psalm 23

*📚 Browse:*
/book Romans
/books - List all 66 books

*🌅 Daily Verses:*
/votd - Verse of the Day
/random - Random verse
/subscribe - Auto daily verse at 6 AM
/unsubscribe - Stop daily verses
/settimezone - Set your timezone
/mystatus - Check subscription
/testdaily - Test daily verse

*💡 Topics:*
salvation, love, faith, prayer, hope, peace, strength, forgiveness, fear, healing, wisdom, anxiety, joy
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
                    f"⏰ You'll receive daily verses at 6:00 AM your local time!",
                    parse_mode='Markdown'
                )
            else:
                context.user_data['timezone'] = tz_value
                await update.message.reply_text(
                    f"✅ *Timezone set!*\n\n"
                    f"🌍 {tz_name}\n\n"
                    f"Now use /subscribe to receive daily verses at 6 AM!",
                    parse_mode='Markdown'
                )
            return
    
    response = "🌍 *Select Your Timezone*\n\n"
    for key, (name, _) in TIMEZONE_OPTIONS.items():
        response += f"{key}. {name}\n"
    response += "\n*Usage:* /settimezone <number>\n"
    response += "*Example:* /settimezone 1"
    
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
            f"⏰ Daily verse at 6:00 AM your time\n\n"
            f"Use /settimezone to change timezone\n"
            f"Use /unsubscribe to stop."
        )
        return
    
    timezone = context.user_data.get('timezone', None)
    
    if not timezone:
        response = "🌍 *Please set your timezone first!*\n\n"
        for key, (name, _) in TIMEZONE_OPTIONS.items():
            response += f"{key}. {name}\n"
        response += "\n*Usage:* /settimezone <number>\n"
        response += "*Example:* /settimezone 1\n\n"
        response += "Then use /subscribe again!"
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
            f"🌍 Timezone: {tz_display}\n"
            f"⏰ Daily verse at 6:00 AM your local time!\n\n"
            f"👥 Total subscribers: {total}\n\n"
            f"Use /settimezone to change timezone\n"
            f"Use /unsubscribe to stop\n"
            f"Use /votd to get today's verse now!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to subscribe. Please try again.")


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_subscribed(chat_id):
        await update.message.reply_text(
            "ℹ️ You're not subscribed to daily verses.\n\n"
            "Use /subscribe to start receiving daily verses!"
        )
        return
    
    if remove_subscriber(chat_id):
        await update.message.reply_text(
            "👋 *Successfully unsubscribed*\n\n"
            "You will no longer receive daily verses.\n\n"
            "Use /subscribe anytime to start again!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to unsubscribe. Please try again.")


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
        
        response = (
            f"✅ *You are subscribed!*\n\n"
            f"🌍 Timezone: {tz_display}\n"
            f"⏰ Daily verse: 6:00 AM your local time\n"
            f"👥 Total subscribers: {total}\n\n"
            f"Use /settimezone to change timezone\n"
            f"Use /unsubscribe to stop."
        )
    else:
        response = (
            "❌ *You are not subscribed*\n\n"
            "Use /settimezone to set your timezone\n"
            "Then /subscribe to get daily verses at 6 AM!"
        )
    
    await update.message.reply_text(response, parse_mode='Markdown')


async def testdaily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_subscribed(chat_id):
        await update.message.reply_text("❌ You're not subscribed. Use /subscribe first.")
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
        f"📍 Your timezone: `{tz_str}`\n"
        f"🕐 Your local time: `{user_time.strftime('%H:%M:%S')}`\n"
        f"📅 Your local date: `{user_time.strftime('%Y-%m-%d')}`\n\n"
        f"Sending test verse now...",
        parse_mode='Markdown'
    )
    
    verse = get_verse_of_the_day()
    if verse:
        book, chapter, verse_num, text = verse
        today = date.today().strftime("%B %d, %Y")
        message = f"🌅 *Test Daily Verse*\n"
        message += f"📅 _{today}_\n\n"
        message += f"📖 *{book} {chapter}:{verse_num}*\n\n"
        message += f"_{text}_\n\n"
        message += "🙏 Have a blessed day!"
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
        response = "❌ Could not get verse of the day."
    await update.message.reply_text(response, parse_mode='Markdown')


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_random_verse()
    if verse:
        book, chapter, verse_num, text = verse
        response = f"🎲 *Random Verse*\n\n📖 *{book} {chapter}:{verse_num}*\n\n_{text}_"
    else:
        response = "❌ Could not get a random verse."
    await update.message.reply_text(response, parse_mode='Markdown')


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a word to search.\n\nExample: /search love")
        return
    keyword = ' '.join(context.args)
    results = search_bible(keyword)
    if not results:
        await update.message.reply_text(f"❌ No verses found for '{keyword}'")
        return
    response = f"🔍 *Found {len(results)} verse(s) for '{keyword}':*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = get_all_topics()
    response = "📚 *Available Topics:*\n\n"
    for i, topic in enumerate(topics, 1):
        response += f"{i}. {topic.title()}\n"
    response += "\n*Usage:* /topic <name>\n*Example:* /topic salvation"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        topics = get_all_topics()
        response = "Please provide a topic name.\n\n*Available topics:*\n"
        response += ", ".join([t.title() for t in topics])
        response += "\n\n*Example:* /topic salvation"
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    topic_name = ' '.join(context.args).lower()
    results = get_verses_by_topic(topic_name)
    if not results:
        topics = get_all_topics()
        response = f"❌ Topic '{topic_name}' not found.\n\n*Available topics:*\n"
        response += ", ".join([t.title() for t in topics])
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    response = f"📚 *Topic: {topic_name.title()}*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide book, chapter and verse.\n\nExample: /verse John 3:16")
        return
    text = ' '.join(context.args)
    try:
        if ':' not in text:
            await update.message.reply_text("Please use format: /verse Book Chapter:Verse")
            return
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]
        chapter, verse = chapter_verse.split(':')
        chapter = int(chapter)
        verse = int(verse)
    except:
        await update.message.reply_text("Please use format: /verse Book Chapter:Verse")
        return
    result = get_specific_verse(book_name, chapter, verse)
    if result:
        book, chap, ver, text = result
        response = f"📖 *{book} {chap}:{ver}*\n\n_{text}_"
    else:
        response = f"❌ Verse not found: {book_name} {chapter}:{verse}"
    await update.message.reply_text(response, parse_mode='Markdown')


async def chapter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide book and chapter.\n\nExample: /chapter Psalm 23")
        return
    text = ' '.join(context.args)
    try:
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter = int(parts[1])
    except:
        await update.message.reply_text("Please use format: /chapter Book Chapter")
        return
    results = get_chapter(book_name, chapter)
    if not results:
        await update.message.reply_text(f"❌ Chapter not found: {book_name} {chapter}")
        return
    response = f"📖 *{book_name.title()} Chapter {chapter}*\n\n"
    for verse_num, text in results[:30]:
        response += f"*{verse_num}.* {text}\n\n"
    if len(results) > 30:
        response += f"_(Showing 30 of {len(results)} verses)_"
    await update.message.reply_text(response, parse_mode='Markdown')


async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a book name.\n\nExample: /book John")
        return
    book_name = ' '.join(context.args)
    results = search_by_book(book_name)
    if not results:
        await update.message.reply_text(f"❌ Book not found: {book_name}\n\nUse /books to see all books.")
        return
    response = f"📚 *Verses from {book_name.title()}:*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    books = get_all_books()
    old_testament = [b[0] for b in books if b[1] == "Old"]
    new_testament = [b[0] for b in books if b[1] == "New"]
    response = "📚 *Bible Books*\n\n*Old Testament (39):*\n"
    response += ", ".join(old_testament[:20]) + "\n" + ", ".join(old_testament[20:]) + "\n\n"
    response += "*New Testament (27):*\n" + ", ".join(new_testament)
    await update.message.reply_text(response, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if not keyword:
        return
    results = search_bible(keyword)
    if not results:
        await update.message.reply_text(f"❌ No verses found for '{keyword}'")
        return
    response = f"🔍 *Found {len(results)} verse(s) for '{keyword}':*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def check_and_send_daily_verses(context: ContextTypes.DEFAULT_TYPE):
    print(f"⏰ Hourly check running at {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    
    subscribers = get_all_subscribers()
    
    if not subscribers:
        print("📭 No subscribers found", flush=True)
        return
    
    print(f"👥 Checking {len(subscribers)} subscribers...", flush=True)
    
    verse = get_verse_of_the_day()
    if not verse:
        print("❌ Could not get verse for daily send", flush=True)
        return
    
    book, chapter, verse_num, text = verse
    today = date.today().strftime("%B %d, %Y")
    
    message = f"🌅 *Good Morning! Daily Verse*\n"
    message += f"📅 _{today}_\n\n"
    message += f"📖 *{book} {chapter}:{verse_num}*\n\n"
    message += f"_{text}_\n\n"
    message += "🙏 Have a blessed day!\n\n"
    message += "_Reply /unsubscribe to stop daily verses_"
    
    sent_count = 0
    
    for chat_id, timezone_str in subscribers:
        try:
            if not timezone_str:
                timezone_str = 'UTC'
            
            tz = pytz.timezone(timezone_str)
            user_time = datetime.now(tz)
            
            print(f"  👤 User {chat_id}: TZ={timezone_str}, LocalTime={user_time.strftime('%H:%M')}", flush=True)
            
            if user_time.hour == 6:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                sent_count += 1
                print(f"  ✅ Sent to {chat_id}", flush=True)
                
        except Exception as e:
            print(f"  ❌ Error for {chat_id}: {e}", flush=True)
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                remove_subscriber(chat_id)
                print(f"  🗑️ Removed invalid subscriber: {chat_id}", flush=True)
    
    print(f"📤 Hourly check complete: {sent_count} messages sent", flush=True)


def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!", flush=True)
        return
    
    print("=" * 50, flush=True)
    print("🤖 Starting Bible Bot...", flush=True)
    print("=" * 50, flush=True)
    
    setup_subscribers_table()
    keep_alive()
    
    bot_app = Application.builder().token(TOKEN).build()
    
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
    
    job_queue = bot_app.job_queue
    job_queue.run_repeating(
        check_and_send_daily_verses,
        interval=3600,
        first=10
    )
    print("📅 Hourly timezone check scheduled", flush=True)
    
    subscriber_count = get_subscriber_count()
    print(f"👥 Current subscribers: {subscriber_count}", flush=True)
    print("✅ Bible Bot is running!", flush=True)
    
    bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
