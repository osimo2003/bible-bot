import sqlite3
import random
import os
from datetime import date, time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread


# GET TOKEN FROM ENVIRONMENT VARIABLE (SECURE)
TOKEN = os.environ.get("BOT_TOKEN")

DB_PATH = "bible.db"

DAILY_HOUR = 12  # 6 AM
DAILY_MINUTE = 15


flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bible Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()


# ============================================
# DATABASE SETUP FOR SUBSCRIBERS
# ============================================

def setup_subscribers_table():
    """Create subscribers table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_date TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Subscribers table ready")


def add_subscriber(chat_id, username=None, first_name=None):
    """Add a user to daily verse subscribers"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO subscribers (chat_id, username, first_name, subscribed_date)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, username, first_name, date.today().isoformat()))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error adding subscriber: {e}")
        success = False
    conn.close()
    return success


def remove_subscriber(chat_id):
    """Remove a user from daily verse subscribers"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0


def is_subscribed(chat_id):
    """Check if user is subscribed"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM subscribers WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_all_subscribers():
    """Get all subscriber chat IDs"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM subscribers')
    results = cursor.fetchall()
    conn.close()
    return [r[0] for r in results]


def get_subscriber_count():
    """Get total number of subscribers"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM subscribers')
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ============================================
# BIBLE DATABASE FUNCTIONS
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
    sub_status = "✅ Subscribed to daily verses" if subscribed else "❌ Not subscribed yet"
    
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
/verse Psalm 23:1

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
/mystatus - Check subscription

*💡 Topics Available:*
salvation, love, faith, prayer, hope, peace, strength, forgiveness, fear, healing, wisdom, anxiety, joy, marriage, money, death, heaven, anger, patience, trust
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe user to daily verses"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    username = user.username if user else None
    first_name = user.first_name if user else None
    
    if is_subscribed(chat_id):
        await update.message.reply_text(
            "✅ You're already subscribed to daily verses!\n\n"
            f"📅 You'll receive verses every day at {DAILY_HOUR}:00 AM\n\n"
            "Use /unsubscribe to stop."
        )
        return
    
    if add_subscriber(chat_id, username, first_name):
        total = get_subscriber_count()
        await update.message.reply_text(
            "🎉 *Successfully subscribed!*\n\n"
            f"📅 You'll receive a verse every day at {DAILY_HOUR}:00 AM\n\n"
            f"👥 Total subscribers: {total}\n\n"
            "Use /unsubscribe anytime to stop.\n"
            "Use /votd to get today's verse now!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to subscribe. Please try again.")


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe user from daily verses"""
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
    """Check subscription status"""
    chat_id = update.effective_chat.id
    
    if is_subscribed(chat_id):
        total = get_subscriber_count()
        response = (
            "✅ *You are subscribed!*\n\n"
            f"📅 Daily verse time: {DAILY_HOUR}:00 AM\n"
            f"👥 Total subscribers: {total}\n\n"
            "Use /unsubscribe to stop."
        )
    else:
        response = (
            "❌ *You are not subscribed*\n\n"
            "Use /subscribe to get daily verses automatically!"
        )
    
    await update.message.reply_text(response, parse_mode='Markdown')


async def votd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_verse_of_the_day()
    if verse:
        book, chapter, verse_num, text = verse
        today = date.today().strftime("%B %d, %Y")
        response = f"🌅 *Verse of the Day*\n"
        response += f"📅 _{today}_\n\n"
        response += f"📖 *{book} {chapter}:{verse_num}*\n\n"
        response += f"_{text}_\n\n"
        response += "🙏 Have a blessed day!"
    else:
        response = "❌ Could not get verse of the day."
    await update.message.reply_text(response, parse_mode='Markdown')


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_random_verse()
    if verse:
        book, chapter, verse_num, text = verse
        response = f"🎲 *Random Verse*\n\n"
        response += f"📖 *{book} {chapter}:{verse_num}*\n\n"
        response += f"_{text}_"
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
        response += f"📖 *{book} {chapter}:{verse}*\n"
        response += f"_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = get_all_topics()
    response = "📚 *Available Topics:*\n\n"
    for i, topic in enumerate(topics, 1):
        response += f"{i}. {topic.title()}\n"
    response += "\n*Usage:* /topic <name>\n"
    response += "*Example:* /topic salvation"
    await update.message.reply_text(response, parse_mode='Markdown')


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        topics = get_all_topics()
        response = "Please provide a topic name.\n\n"
        response += "*Available topics:*\n"
        response += ", ".join([t.title() for t in topics])
        response += "\n\n*Example:* /topic salvation"
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    topic_name = ' '.join(context.args).lower()
    results = get_verses_by_topic(topic_name)
    if not results:
        topics = get_all_topics()
        response = f"❌ Topic '{topic_name}' not found.\n\n"
        response += "*Available topics:*\n"
        response += ", ".join([t.title() for t in topics])
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    response = f"📚 *Topic: {topic_name.title()}*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n"
        response += f"_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Please provide book, chapter and verse.\n\n"
            "Examples:\n"
            "/verse John 3:16\n"
            "/verse Genesis 1:1\n"
            "/verse Psalm 23:1"
        )
        return
    text = ' '.join(context.args)
    try:
        if ':' not in text:
            await update.message.reply_text("Please use format: /verse Book Chapter:Verse\n\nExample: /verse John 3:16")
            return
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]
        chapter, verse = chapter_verse.split(':')
        chapter = int(chapter)
        verse = int(verse)
    except (ValueError, IndexError):
        await update.message.reply_text("Please use format: /verse Book Chapter:Verse\n\nExample: /verse John 3:16")
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
        await update.message.reply_text(
            "Please provide book and chapter.\n\n"
            "Examples:\n"
            "/chapter John 3\n"
            "/chapter Psalm 23"
        )
        return
    text = ' '.join(context.args)
    try:
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter = int(parts[1])
    except (ValueError, IndexError):
        await update.message.reply_text("Please use format: /chapter Book Chapter\n\nExample: /chapter John 3")
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
        await update.message.reply_text(
            "Please provide a book name.\n\n"
            "Examples:\n"
            "/book John\n"
            "/book Genesis"
        )
        return
    book_name = ' '.join(context.args)
    results = search_by_book(book_name)
    if not results:
        await update.message.reply_text(f"❌ Book not found: {book_name}\n\nUse /books to see all books.")
        return
    response = f"📚 *Verses from {book_name.title()}:*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n"
        response += f"_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    books = get_all_books()
    old_testament = [b[0] for b in books if b[1] == "Old"]
    new_testament = [b[0] for b in books if b[1] == "New"]
    response = "📚 *Bible Books*\n\n"
    response += "*Old Testament (39):*\n"
    response += ", ".join(old_testament[:20]) + "\n"
    response += ", ".join(old_testament[20:]) + "\n\n"
    response += "*New Testament (27):*\n"
    response += ", ".join(new_testament)
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
        response += f"📖 *{book} {chapter}:{verse}*\n"
        response += f"_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


# ============================================
# DAILY VERSE AUTO-SEND
# ============================================

async def send_daily_verse(context: ContextTypes.DEFAULT_TYPE):
    """Send daily verse to all subscribers automatically"""
    verse = get_verse_of_the_day()
    
    if not verse:
        print("❌ Could not get verse for daily send")
        return
    
    book, chapter, verse_num, text = verse
    today = date.today().strftime("%B %d, %Y")
    
    message = f"🌅 *Good Morning! Daily Verse*\n"
    message += f"📅 _{today}_\n\n"
    message += f"📖 *{book} {chapter}:{verse_num}*\n\n"
    message += f"_{text}_\n\n"
    message += "🙏 Have a blessed day!\n\n"
    message += "_Reply /unsubscribe to stop daily verses_"
    
    subscribers = get_all_subscribers()
    success_count = 0
    fail_count = 0
    
    print(f"📤 Sending daily verse to {len(subscribers)} subscribers...")
    
    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to send to {chat_id}: {e}")
            # Remove invalid subscribers (blocked bot, deleted account)
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                remove_subscriber(chat_id)
                print(f"🗑️ Removed invalid subscriber: {chat_id}")
            fail_count += 1
    
    print(f"✅ Daily verse sent: {success_count} success, {fail_count} failed")


# ============================================
# MAIN FUNCTION
# ============================================

def main():
    # Check if token exists
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!")
        print("Set it with: export BOT_TOKEN=your_token_here")
        return
    
    print("=" * 50)
    print("🤖 Starting Bible Bot...")
    print("=" * 50)
    
    # Setup subscribers table
    setup_subscribers_table()
    
    # Start Flask server for keep-alive
    keep_alive()
    
    # Create bot application
    bot_app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
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
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Schedule daily verse at 6 AM
    job_queue = bot_app.job_queue
    job_queue.run_daily(
        send_daily_verse,
        time=time(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        name="daily_verse"
    )
    print(f"📅 Daily verse scheduled for {DAILY_HOUR}:{DAILY_MINUTE:02d} AM")
    
    subscriber_count = get_subscriber_count()
    print(f"👥 Current subscribers: {subscriber_count}")
    print("")
    print("✅ Bible Bot is running!")
    
    bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
