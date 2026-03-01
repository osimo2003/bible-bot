import sqlite3
import random
import os
import re
import asyncio
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

# ─────────────────────────────────────────────────────────────
# SMART SEARCH ENGINE
# ─────────────────────────────────────────────────────────────

# Words that carry no useful meaning for a Bible search
STOP_WORDS = {
    # Pronouns & common grammar
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'want', 'like',
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
    'this', 'that', 'these', 'those', 'what', 'which', 'who', 'how', 'when',
    'where', 'why', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
    'other', 'some', 'such', 'than', 'then', 'so', 'just', 'because',
    'as', 'not', 'no', 'nor', 'only', 'own', 'same', 'too', 'very',
    'also', 'back', 'still', 'well', 'way', 'even', 'new', 'want',
    'since', 'while', 'after', 'before', 'now', 'here', 'there',

    # Bible-request filler words
    'bible', 'verse', 'verses', 'scripture', 'scriptures', 'passage',
    'passages', 'give', 'show', 'find', 'get', 'send', 'tell', 'read',
    'say', 'says', 'said', 'speak', 'speaks', 'talk', 'talks',
    'regarding', 'concerning', 'related', 'topic', 'something', 'anything',
    'please', 'help', 'helps', 'know', 'knows', 'look', 'looking', 'search',
    'need', 'needs', 'want', 'wants', 'looking', 'seeking', 'seek',
}

# Maps modern/varied words → root Bible search term
WORD_SYNONYMS = {
    # ── Emotions ──
    'scared':        'fear',
    'fearful':       'fear',
    'afraid':        'fear',
    'frightened':    'fear',
    'worry':         'fear',
    'worrying':      'fear',
    'worried':       'fear',
    'anxious':       'anxiety',
    'nervous':       'anxiety',
    'stress':        'anxiety',
    'stressed':      'anxiety',
    'overthinking':  'anxiety',
    'depressed':     'sorrow',
    'depression':    'sorrow',
    'sad':           'sorrow',
    'sadness':       'sorrow',
    'unhappy':       'sorrow',
    'crying':        'weep',
    'cry':           'weep',
    'tears':         'weep',
    'happy':         'joy',
    'happiness':     'joy',
    'joyful':        'joy',
    'glad':          'joy',
    'angry':         'anger',
    'mad':           'anger',
    'furious':       'anger',
    'rage':          'anger',
    'bitterness':    'bitter',
    'bitter':        'bitter',
    'jealous':       'envy',
    'jealousy':      'envy',
    'envious':       'envy',
    'shame':         'shame',
    'ashamed':       'shame',
    'embarrassed':   'shame',
    'guilt':         'guilt',
    'guilty':        'guilt',

    # ── Faith & Spiritual ──
    'sins':          'sin',
    'sinning':       'sin',
    'sinful':        'sin',
    'sinner':        'sin',
    'sinners':       'sin',
    'praying':       'prayer',
    'pray':          'prayer',
    'prayers':       'prayer',
    'believing':     'faith',
    'believe':       'faith',
    'belief':        'faith',
    'unbelief':      'doubt',
    'doubting':      'doubt',
    'trusting':      'trust',
    'trusted':       'trust',
    'hopeful':       'hope',
    'hoping':        'hope',
    'loves':         'love',
    'loved':         'love',
    'loving':        'love',
    'lover':         'love',
    'forgiving':     'forgiveness',
    'forgive':       'forgiveness',
    'forgiven':      'forgiveness',
    'forgives':      'forgiveness',
    'saved':         'salvation',
    'saving':        'salvation',
    'savior':        'salvation',
    'redeem':        'redemption',
    'redeemed':      'redemption',
    'bless':         'blessing',
    'blessed':       'blessing',
    'blessings':     'blessing',
    'healed':        'healing',
    'heals':         'healing',
    'heal':          'healing',
    'sick':          'healing',
    'sickness':      'healing',
    'illness':       'healing',
    'disease':       'healing',
    'holy':          'holiness',
    'gracious':      'grace',
    'merciful':      'mercy',
    'mercies':       'mercy',
    'righteous':     'righteousness',
    'righteously':   'righteousness',
    'wicked':        'wickedness',
    'evil':          'wickedness',
    'repent':        'repentance',
    'repenting':     'repentance',
    'repentance':    'repentance',
    'confess':       'confession',
    'confessing':    'confession',
    'baptism':       'baptism',
    'baptized':      'baptism',
    'anointing':     'anoint',
    'anointed':      'anoint',
    'fasting':       'fast',
    'fast':          'fast',

    # ── Life Situations ──
    'strong':        'strength',
    'stronger':      'strength',
    'strengthen':    'strength',
    'weak':          'weakness',
    'weaknesses':    'weakness',
    'tired':         'weary',
    'exhausted':     'weary',
    'burnout':       'weary',
    'waiting':       'wait',
    'lonely':        'alone',
    'loneliness':    'alone',
    'difficult':     'trouble',
    'difficulties':  'trouble',
    'hardship':      'trouble',
    'struggling':    'trouble',
    'struggle':      'trouble',
    'suffering':     'suffer',
    'suffers':       'suffer',
    'poor':          'poverty',
    'rich':          'wealth',
    'riches':        'wealth',
    'wealthy':       'wealth',
    'money':         'wealth',
    'finances':      'wealth',
    'debt':          'debt',
    'dying':         'death',
    'died':          'death',
    'dead':          'death',
    'grieving':      'grief',
    'grieve':        'grief',
    'mourning':      'grief',
    'mourn':         'grief',
    'lost':          'lost',
    'losing':        'lost',
    'broken':        'broken',
    'brokenness':    'broken',
    'enemies':       'enemy',
    'war':           'battle',
    'wars':          'battle',
    'fighting':      'battle',
    'overcome':      'victory',
    'overcoming':    'victory',
    'succeed':       'prosper',
    'success':       'prosper',
    'prosper':       'prosper',
    'failing':       'fail',
    'failure':       'fail',
    'disappointed':  'fail',
    'rejection':     'rejected',
    'rejected':      'rejected',
    'tempted':       'temptation',
    'tempting':      'temptation',
    'addicted':      'temptation',
    'addiction':     'temptation',
    'abuse':         'oppression',
    'oppressed':     'oppression',
    'injustice':     'justice',
    'justice':       'justice',
    'protection':    'protect',
    'protect':       'protect',
    'safe':          'protect',
    'safety':        'protect',
    'danger':        'protect',

    # ── Relationships ──
    'marriage':      'wife',
    'married':       'wife',
    'divorce':       'divorce',
    'children':      'child',
    'kids':          'child',
    'parents':       'father',
    'friendship':    'friend',
    'friends':       'friend',
    'neighbor':      'neighbour',
    'neighbours':    'neighbour',
    'neighbors':     'neighbour',

    # ── Character & Virtues ──
    'wise':          'wisdom',
    'wisely':        'wisdom',
    'wiser':         'wisdom',
    'humble':        'humility',
    'honest':        'truth',
    'honesty':       'truth',
    'truthful':      'truth',
    'kind':          'kindness',
    'caring':        'kindness',
    'generous':      'generosity',
    'generosity':    'generosity',
    'giving':        'give',
    'courageous':    'courage',
    'brave':         'courage',
    'bravery':       'courage',
    'bold':          'courage',
    'boldness':      'courage',
    'faithful':      'faithful',
    'faithfully':    'faithful',
    'obedient':      'obey',
    'obedience':     'obey',
    'serving':       'serve',
    'servant':       'serve',
    'service':       'serve',
    'diligent':      'diligence',
    'diligence':     'diligence',
    'hardworking':   'diligence',
    'lazy':          'slothful',
    'selfless':      'selfless',
    'selfish':       'selfish',
    'pride':         'pride',
    'proud':         'pride',
    'arrogant':      'pride',

    # ── God & Jesus ──
    'god':           'lord',
    'jesus':         'jesus',
    'christ':        'christ',
    'spirit':        'spirit',
    'heaven':        'heaven',
    'eternal':       'eternal',
    'eternity':      'eternal',
    'everlasting':   'eternal',
    'worshipping':   'worship',
    'praising':      'praise',
    'glorify':       'glory',
    'glorifying':    'glory',
    'kingdom':       'kingdom',
    'commandment':   'commandments',
    'commandments':  'commandments',
    'law':           'law',
    'covenant':      'covenant',
    'promise':       'promise',
    'promises':      'promise',

    # ── Two-word phrases ──
    'holy spirit':   'spirit',
    'broken heart':  'broken',
    'second coming': 'coming',
    'end times':     'tribulation',
    'new life':      'born',
    'new beginning': 'renew',
    'mental health': 'anxiety',
    'self worth':    'worth',
    'self control':  'temperance',
    'self esteem':   'worth',
    'inner peace':   'peace',
    'hard times':    'trouble',
    'bad times':     'trouble',
    'difficult times':'trouble',
    'dark times':    'trouble',
    'moving on':     'forgiveness',
    'letting go':    'forgiveness',
    'starting over': 'renew',
    'born again':    'born',
}


def extract_search_keywords(user_input):
    """
    Breaks down ANY phrase or sentence into useful Bible search keywords.

    Examples:
      'i need a verse about being strong in difficult times'
        → ['strength', 'trouble']

      'what does the bible say about forgiving your enemies'
        → ['forgiveness', 'enemy']

      'help me with anxiety and depression'
        → ['anxiety', 'sorrow']

      'how do i deal with loneliness after a breakup'
        → ['alone', 'sorrow']
    """
    text = user_input.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)        # collapse spaces

    words = text.split()
    keywords = []
    seen = set()
    skip_next = False

    for i, word in enumerate(words):
        if skip_next:
            skip_next = False
            continue

        # Check two-word combo first (e.g. "holy spirit", "broken heart")
        if i + 1 < len(words):
            two_word = f"{word} {words[i+1]}"
            if two_word in WORD_SYNONYMS:
                mapped = WORD_SYNONYMS[two_word]
                if mapped not in seen:
                    seen.add(mapped)
                    keywords.append(mapped)
                skip_next = True
                continue

        # Skip stop words and very short words
        if word in STOP_WORDS or len(word) <= 2:
            continue

        # Map to synonym/root if available, otherwise use word directly
        mapped = WORD_SYNONYMS.get(word, word)
        if mapped not in seen:
            seen.add(mapped)
            keywords.append(mapped)

    return keywords if keywords else [user_input.strip()]


def search_bible_smart(user_input, nt_limit=3, ot_limit=2):
    """
    Searches the Bible database intelligently.
    Returns 3 New Testament + 2 Old Testament verses.
    Tries each extracted keyword in turn until slots are filled.
    No duplicate verses returned.
    """
    keywords = extract_search_keywords(user_input)
    print(f"🔑 Extracted keywords: {keywords}", flush=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    nt_results = []
    ot_results = []
    seen_verses = set()

    for keyword in keywords:
        if len(nt_results) >= nt_limit and len(ot_results) >= ot_limit:
            break

        like_kw = f'%{keyword}%'

        if len(nt_results) < nt_limit:
            cursor.execute('''
                SELECT b.book_name, v.chapter, v.verse, v.text
                FROM verses v
                JOIN books b ON v.book_id = b.book_id
                WHERE v.text LIKE ? AND b.testament = 'New'
                ORDER BY RANDOM()
                LIMIT ?
            ''', (like_kw, nt_limit - len(nt_results)))

            for row in cursor.fetchall():
                verse_id = f"{row[0]}{row[1]}:{row[2]}"
                if verse_id not in seen_verses:
                    seen_verses.add(verse_id)
                    nt_results.append(row)

        if len(ot_results) < ot_limit:
            cursor.execute('''
                SELECT b.book_name, v.chapter, v.verse, v.text
                FROM verses v
                JOIN books b ON v.book_id = b.book_id
                WHERE v.text LIKE ? AND b.testament = 'Old'
                ORDER BY RANDOM()
                LIMIT ?
            ''', (like_kw, ot_limit - len(ot_results)))

            for row in cursor.fetchall():
                verse_id = f"{row[0]}{row[1]}:{row[2]}"
                if verse_id not in seen_verses:
                    seen_verses.add(verse_id)
                    ot_results.append(row)

    conn.close()
    return nt_results, ot_results, keywords


# ─────────────────────────────────────────────────────────────
# FLASK KEEP-ALIVE
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────

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


def get_random_verse():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        ORDER BY RANDOM()
        LIMIT 1
    ''')
    result = cursor.fetchone()
    conn.close()
    return result


def get_specific_verse(book_name, chapter, verse):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ? AND v.chapter = ? AND v.verse = ?
    ''', (f'%{book_name}%', chapter, verse))
    result = cursor.fetchone()
    conn.close()
    return result


def get_chapter(book_name, chapter):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ? AND v.chapter = ?
        ORDER BY v.verse
    ''', (f'%{book_name}%', chapter))
    results = cursor.fetchall()
    conn.close()
    return results


def search_by_book(book_name, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name LIKE ?
        LIMIT ?
    ''', (f'%{book_name}%', limit))
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
    random.seed(seed)
    offset = random.randint(0, total - 1)
    cursor.execute('''
        SELECT b.book_name, v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.testament = 'New'
        LIMIT 1 OFFSET ?
    ''', (offset,))
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
    cursor.execute('''
        SELECT b.book_name, t.chapter, t.verse, v.text
        FROM topics t
        JOIN books b ON t.book_id = b.book_id
        JOIN verses v ON t.book_id = v.book_id AND t.chapter = v.chapter AND t.verse = v.verse
        WHERE t.topic_name = ?
        LIMIT ?
    ''', (topic_name.lower(), limit))
    results = cursor.fetchall()
    conn.close()
    return results


# ─────────────────────────────────────────────────────────────
# SHARED RESULT FORMATTER
# ─────────────────────────────────────────────────────────────

async def send_search_results(update, raw_input, keywords, nt_results, ot_results):
    """Formats and sends search results showing NT and OT sections."""

    if not nt_results and not ot_results:
        await update.message.reply_text(
            f"❌ No verses found for *'{raw_input}'*\n\n"
            f"🔑 Searched for: {', '.join(keywords)}\n\n"
            f"Try different words like:\n"
            f"love, faith, hope, peace, strength, wisdom, prayer",
            parse_mode='Markdown'
        )
        return

    keyword_display = ', '.join(f'`{k}`' for k in keywords)
    response = f"🔍 *Results for:* _{raw_input}_\n"
    response += f"🔑 *Searched:* {keyword_display}\n\n"

    if nt_results:
        response += "━━━━━━━━━━━━━━━━\n"
        response += "📖 *New Testament*\n"
        response += "━━━━━━━━━━━━━━━━\n\n"
        for book, chapter, verse, text in nt_results:
            response += f"*{book} {chapter}:{verse}*\n_{text}_\n\n"

    if ot_results:
        response += "━━━━━━━━━━━━━━━━\n"
        response += "📜 *Old Testament*\n"
        response += "━━━━━━━━━━━━━━━━\n\n"
        for book, chapter, verse, text in ot_results:
            response += f"*{book} {chapter}:{verse}*\n_{text}_\n\n"

    await update.message.reply_text(response, parse_mode='Markdown')


# ─────────────────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────

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
/search <word or phrase> - Smart search
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
/search love
/search i need strength in hard times
/search what does the bible say about forgiveness
/search help with anxiety and depression
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

*💬 You can also just TYPE any word or phrase:*
_"give me a verse about courage"_
_"bible verse on overcoming fear"_
_"i feel lost and need comfort"_
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
    except Exception:
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
        message = (
            f"🌅 *Test Daily Verse*\n"
            f"📅 _{today}_\n\n"
            f"📖 *{book} {chapter}:{verse_num}*\n\n"
            f"_{text}_\n\n"
            f"🙏 Have a blessed day!"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Could not get verse.")


async def votd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = get_verse_of_the_day()
    if verse:
        book, chapter, verse_num, text = verse
        today = date.today().strftime("%B %d, %Y")
        response = (
            f"🌅 *Verse of the Day*\n"
            f"📅 _{today}_\n\n"
            f"📖 *{book} {chapter}:{verse_num}*\n\n"
            f"_{text}_\n\n"
            f"🙏 Have a blessed day!"
        )
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
        await update.message.reply_text(
            "Please provide a word or phrase to search.\n\n"
            "*Examples:*\n"
            "• /search love\n"
            "• /search i need strength in hard times\n"
            "• /search what does the bible say about hope\n"
            "• /search help with anxiety and depression\n"
            "• /search forgiving my enemies",
            parse_mode='Markdown'
        )
        return

    raw_input = ' '.join(context.args)
    nt_results, ot_results, keywords = search_bible_smart(raw_input)
    await send_search_results(update, raw_input, keywords, nt_results, ot_results)


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
        await update.message.reply_text(
            "Please provide book, chapter and verse.\n\nExample: /verse John 3:16"
        )
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
    except Exception:
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
        await update.message.reply_text(
            "Please provide book and chapter.\n\nExample: /chapter Psalm 23"
        )
        return

    text = ' '.join(context.args)
    try:
        parts = text.rsplit(' ', 1)
        book_name = parts[0]
        chapter = int(parts[1])
    except Exception:
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
        await update.message.reply_text(
            "Please provide a book name.\n\nExample: /book John"
        )
        return

    book_name = ' '.join(context.args)
    results = search_by_book(book_name)
    if not results:
        await update.message.reply_text(
            f"❌ Book not found: {book_name}\n\nUse /books to see all books."
        )
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
    """
    Handles any plain text message (not a command).
    Uses smart keyword extraction to search the Bible intelligently.
    """
    raw_input = update.message.text.strip()
    if not raw_input:
        return

    nt_results, ot_results, keywords = search_bible_smart(raw_input)
    await send_search_results(update, raw_input, keywords, nt_results, ot_results)


# ─────────────────────────────────────────────────────────────
# DAILY VERSE SCHEDULER — Fixed BST/GMT + Async Sending
# ─────────────────────────────────────────────────────────────

async def check_and_send_daily_verses(context: ContextTypes.DEFAULT_TYPE):
    print(
        f"⏰ Hourly check running at "
        f"{datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        flush=True
    )

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

    message = (
        f"🌅 *Good Morning! Daily Verse*\n"
        f"📅 _{today}_\n\n"
        f"📖 *{book} {chapter}:{verse_num}*\n\n"
        f"_{text}_\n\n"
        f"🙏 Have a blessed day!\n\n"
        f"_Reply /unsubscribe to stop daily verses_"
    )

    # Collect all subscribers whose local time is currently 6 AM
    # pytz handles GMT/BST switching automatically for Europe/London
    targets = []
    for chat_id, timezone_str in subscribers:
        try:
            tz = pytz.timezone(timezone_str or 'UTC')
            user_time = datetime.now(tz)
            print(
                f"  👤 {chat_id}: TZ={timezone_str}, "
                f"LocalTime={user_time.strftime('%H:%M')}",
                flush=True
            )
            if user_time.hour == 6:
                targets.append(chat_id)
        except Exception as e:
            print(f"  ❌ Timezone error for {chat_id}: {e}", flush=True)

    if not targets:
        print("📭 No subscribers at 6 AM right now", flush=True)
        return

    # Send to ALL targets simultaneously — no delay regardless of subscriber count
    async def send_to_one(chat_id):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            print(f"  ✅ Sent to {chat_id}", flush=True)
        except Exception as e:
            print(f"  ❌ Failed for {chat_id}: {e}", flush=True)
            if "blocked" in str(e).lower() or "not found" in str(e).lower():
                remove_subscriber(chat_id)
                print(f"  🗑️ Removed invalid subscriber: {chat_id}", flush=True)

    await asyncio.gather(*[send_to_one(cid) for cid in targets])
    print(f"📤 Done: {len(targets)} messages sent simultaneously", flush=True)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!", flush=True)
        return

    print("=" * 50, flush=True)
    print("🤖 Starting Bible Bot...", flush=True)
    print(f"🕐 Server UTC time: {datetime.now(pytz.UTC)}", flush=True)
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
