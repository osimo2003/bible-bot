import urllib.request
import json
import sqlite3

def setup_database():
    print("📥 Downloading Bible data...")
    
    # Download Bible JSON
    url = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
    urllib.request.urlretrieve(url, "bible.json")
    print("✅ Bible downloaded!")
    
    # Create database
    print("🔨 Creating database...")
    conn = sqlite3.connect('bible.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY,
            book_name TEXT NOT NULL,
            testament TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            chapter INTEGER,
            verse INTEGER,
            text TEXT,
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_name TEXT NOT NULL,
            book_id INTEGER,
            chapter INTEGER,
            verse INTEGER,
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        )
    ''')
    
    # Clear old data
    cursor.execute("DELETE FROM verses")
    cursor.execute("DELETE FROM books")
    cursor.execute("DELETE FROM topics")
    
    # Load Bible
    print("📚 Importing Bible...")
    with open('bible.json', 'r', encoding='utf-8-sig') as f:
        bible = json.load(f)
    
    old_testament = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
        "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
        "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
        "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
        "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
        "Zephaniah", "Haggai", "Zechariah", "Malachi"
    ]
    
    total_verses = 0
    
    for book_index, book in enumerate(bible, 1):
        book_name = book['name']
        testament = "Old" if book_name in old_testament else "New"
        
        cursor.execute(
            "INSERT INTO books (book_id, book_name, testament) VALUES (?, ?, ?)",
            (book_index, book_name, testament)
        )
        
        for chapter_num, chapter in enumerate(book['chapters'], 1):
            for verse_num, verse_text in enumerate(chapter, 1):
                cursor.execute(
                    "INSERT INTO verses (book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                    (book_index, chapter_num, verse_num, verse_text)
                )
                total_verses += 1
    
    print(f"✅ Imported {total_verses} verses!")
    
    # Add topics
    print("📚 Adding topics...")
    topics_data = {
        "salvation": [("John", 3, 16), ("Romans", 10, 9), ("Ephesians", 2, 8), ("Acts", 4, 12), ("Romans", 6, 23)],
        "love": [("1 Corinthians", 13, 4), ("1 John", 4, 8), ("John", 3, 16), ("Romans", 8, 38), ("John", 15, 13)],
        "faith": [("Hebrews", 11, 1), ("Hebrews", 11, 6), ("Romans", 10, 17), ("James", 2, 17), ("Galatians", 2, 20)],
        "prayer": [("Philippians", 4, 6), ("1 Thessalonians", 5, 17), ("Matthew", 6, 9), ("James", 5, 16), ("Jeremiah", 29, 12)],
        "hope": [("Romans", 15, 13), ("Jeremiah", 29, 11), ("Romans", 8, 28), ("Hebrews", 6, 19), ("Isaiah", 40, 31)],
        "peace": [("John", 14, 27), ("Philippians", 4, 7), ("Isaiah", 26, 3), ("Romans", 5, 1), ("Colossians", 3, 15)],
        "strength": [("Philippians", 4, 13), ("Isaiah", 40, 31), ("Psalm", 27, 1), ("2 Corinthians", 12, 9), ("Deuteronomy", 31, 6)],
        "forgiveness": [("1 John", 1, 9), ("Ephesians", 4, 32), ("Colossians", 3, 13), ("Matthew", 6, 14), ("Psalm", 103, 12)],
        "fear": [("Isaiah", 41, 10), ("2 Timothy", 1, 7), ("Psalm", 23, 4), ("Psalm", 27, 1), ("Joshua", 1, 9)],
        "healing": [("Jeremiah", 17, 14), ("Psalm", 103, 3), ("Isaiah", 53, 5), ("James", 5, 15), ("Exodus", 15, 26)],
        "wisdom": [("James", 1, 5), ("Proverbs", 3, 5), ("Proverbs", 2, 6), ("Colossians", 2, 3), ("Proverbs", 9, 10)],
        "anxiety": [("Philippians", 4, 6), ("1 Peter", 5, 7), ("Matthew", 6, 34), ("Psalm", 55, 22), ("Isaiah", 41, 10)],
        "joy": [("Nehemiah", 8, 10), ("Psalm", 16, 11), ("John", 15, 11), ("Romans", 15, 13), ("Philippians", 4, 4)],
        "marriage": [("Genesis", 2, 24), ("Ephesians", 5, 25), ("1 Corinthians", 13, 4), ("Proverbs", 18, 22), ("Hebrews", 13, 4)],
        "money": [("Matthew", 6, 24), ("Hebrews", 13, 5), ("1 Timothy", 6, 10), ("Proverbs", 22, 7), ("Malachi", 3, 10)],
        "death": [("John", 11, 25), ("Psalm", 23, 4), ("Romans", 8, 38), ("1 Corinthians", 15, 55), ("Revelation", 21, 4)],
        "heaven": [("John", 14, 2), ("Revelation", 21, 4), ("Philippians", 3, 20), ("Matthew", 6, 20), ("1 Corinthians", 2, 9)],
        "anger": [("James", 1, 19), ("Proverbs", 15, 1), ("Ephesians", 4, 26), ("Proverbs", 14, 29), ("Colossians", 3, 8)],
        "patience": [("James", 1, 4), ("Romans", 12, 12), ("Galatians", 6, 9), ("Ecclesiastes", 7, 8), ("Colossians", 3, 12)],
        "trust": [("Proverbs", 3, 5), ("Psalm", 37, 5), ("Isaiah", 26, 4), ("Jeremiah", 17, 7), ("Psalm", 56, 3)],
    }
    
    for topic_name, verses in topics_data.items():
        for book_name, chapter, verse in verses:
            cursor.execute("SELECT book_id FROM books WHERE book_name LIKE ?", (f'%{book_name}%',))
            result = cursor.fetchone()
            if result:
                cursor.execute(
                    "INSERT INTO topics (topic_name, book_id, chapter, verse) VALUES (?, ?, ?, ?)",
                    (topic_name, result[0], chapter, verse)
                )
    
    conn.commit()
    conn.close()
    
    print("✅ Database setup complete!")


if __name__ == "__main__":
    setup_database()
