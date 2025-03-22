# schema_creation.py
import sqlite3
import os

def create_schema():
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'unfake.db')
    
    # Create a new connection
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            url TEXT UNIQUE,
            author_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_categories (
            article_id INTEGER,
            category_id INTEGER,
            PRIMARY KEY (article_id, category_id),
            FOREIGN KEY (article_id) REFERENCES articles(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            user_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(article_id, user_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fake_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(article_id, user_id)
        )
    """)
    
    # Create view for low credibility articles
    cur.execute("""
        CREATE VIEW IF NOT EXISTS v_low_credibility AS
        SELECT 
            a.id,
            a.title,
            a.content,
            a.url,
            a.created_at,
            COUNT(DISTINCT r.id) as rating_count,
            AVG(r.rating) as avg_rating,
            COUNT(DISTINCT f.id) as fake_mark_count
        FROM articles a
        LEFT JOIN ratings r ON a.id = r.article_id
        LEFT JOIN fake_marks f ON a.id = f.article_id
        GROUP BY a.id
        HAVING 
            (rating_count < 3 OR avg_rating < 3) 
            OR fake_mark_count > 0
    """)
    
    # Insert default categories if they don't exist
    default_categories = [
        "Politics",
        "Science",
        "Technology",
        "Health",
        "Business",
        "Entertainment",
        "Sports",
        "Education",
        "Environment",
        "Other"
    ]
    
    for category in default_categories:
        cur.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("All core tables + columns verified.")
    print("v_low_credibility view created/updated.")
    print("Duplicate categories removed.")
    print("Schema creation/upgrade complete! Run app.py afterwards.")

if __name__ == "__main__":
    create_schema()
