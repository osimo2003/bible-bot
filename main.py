import sqlite3
import random
import os
from datetime import date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# ⚠️ REPLACE WITH YOUR ACTUAL TOKEN
TOKEN = os.environ.get("BOT_TOKEN", "8414803318:AAGGVJwSu_QATtvFQ8IDSflrbIi8V-J6Uws")

# Database path
DB_PATH = "bible.db"

# Flask app to keep alive
app = Flask('')

@app.route('/')
def home():
    return "🙏 Bible Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    welcome = f"""
🙏 *Welcome to Bible Bot!*

Your Chat ID: `{chat_id}`

*📚 Commands:*

/search <word> - Search for verses
/topic <topic> - Search by topic
/topics - List all topics
/verse John 3:16 - Get specific verse
/chapter Psalm 23 - Get full chapter
/book Romans - Browse a book
/books - List all 66 books
/votd - Verse of the Day
/random - Random verse
/help - Show all commands

Or just type any word to search!
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

*🌅 Daily:*
/votd - Verse of the Day
/random - Random verse

*💡 Topics:*
salvation, love, faith, prayer, hope, peace, strength, forgiveness, fear, healing, wisdom, anxiety, joy, marriage, money, death, heaven, anger, patience, trust
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


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
        await update.message.reply_text("Please provide a word.\n\nExample: /search love")
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
        response = "Please provide a topic.\n\n*Available:*\n" + ", ".join([t.title() for t in topics])
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    topic_name = ' '.join(context.args).lower()
    results = get_verses_by_topic(topic_name)
    if not results:
        topics = get_all_topics()
        response = f"❌ Topic '{topic_name}' not found.\n\n*Available:*\n" + ", ".join([t.title() for t in topics])
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    response = f"📚 *Topic: {topic_name.title()}*\n\n"
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
            await update.message.reply_text("Use format: /verse Book Chapter:Verse")
            return
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]
        chapter, verse = chapter_verse.split(':')
        chapter = int(chapter)
        verse = int(verse)
    except:
        await update.message.reply_text("Use format: /verse Book Chapter:Verse")
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
        await update.message.reply_text("Example: /chapter Psalm 23")
        return
    text = ' '.join(context.args)
    try:
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter = int(parts[1])
    except:
        await update.message.reply_text("Use format: /chapter Book Chapter")
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
        await update.message.reply_text("Example: /book John")
        return
    book_name = ' '.join(context.args)
    results = search_by_book(book_name)
    if not results:
        await update.message.reply_text(f"❌ Book not found: {book_name}")
        return
    response = f"📚 *Verses from {book_name.title()}:*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
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
        await update.message.reply_text(f"❌ No verses found for '{keyword}'")
        return
    response = f"🔍 *Found {len(results)} verse(s) for '{keyword}':*\n\n"
    for book, chapter, verse, text in results:
        response += f"📖 *{book} {chapter}:{verse}*\n_{text}_\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')


def main():
    # Setup database if not exists
    if not os.path.exists(DB_PATH):
        print("📚 Setting up Bible database...")
        from setup_database import setup_database
        setup_database()
    
    print("🤖 Starting Bible Bot...")
    
    # Keep alive
    keep_alive()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("votd", votd_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("topics", topics_command))
    app.add_handler(CommandHandler("topic", topic_command))
    app.add_handler(CommandHandler("verse", verse_command))
    app.add_handler(CommandHandler("chapter", chapter_command))
    app.add_handler(CommandHandler("book", book_command))
    app.add_handler(CommandHandler("books", books_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot is running 24/7!")
    app.run_polling()


if __name__ == "__main__":
    main()
