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
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            join_date DATE DEFAULT CURRENT_DATE,
            profile_picture TEXT DEFAULT '',
            bio TEXT DEFAULT ''
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            article_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            contents TEXT NOT NULL,
            author_name TEXT NOT NULL,
            publication_date DATE DEFAULT CURRENT_DATE,
            submitter_id INTEGER,
            source_link TEXT,
            overall_rating REAL DEFAULT 0,
            is_fake INTEGER DEFAULT 0,
            ml_score REAL DEFAULT 0,
            FOREIGN KEY (submitter_id) REFERENCES users(user_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT ''
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_category (
            article_id INTEGER,
            category_id INTEGER,
            PRIMARY KEY (article_id, category_id),
            FOREIGN KEY (article_id) REFERENCES articles(article_id),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            user_id INTEGER,
            rating_value INTEGER CHECK(rating_value >= 1 AND rating_value <= 5),
            comment TEXT,
            rating_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(article_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(article_id, user_id)
        )
    """)
    
    # Create view for low credibility articles
    cur.execute("""
        CREATE VIEW IF NOT EXISTS v_low_credibility AS
        SELECT 
            a.article_id,
            a.title,
            a.author_name,
            a.overall_rating
        FROM articles a
        WHERE a.is_fake = 1 AND a.overall_rating >= 3
    """)
    
    # Insert default categories if they don't exist
    default_categories = [
        ("Politics", "Political news and updates"),
        ("Science", "Scientific discoveries and research"),
        ("Technology", "Tech news and innovations"),
        ("Health", "Health and medical news"),
        ("Business", "Business and economic news"),
        ("Entertainment", "Entertainment and celebrity news"),
        ("Sports", "Sports news and updates"),
        ("Education", "Education and academic news"),
        ("Environment", "Environmental news and climate updates"),
        ("Other", "Other news categories")
    ]
    
    for category_name, description in default_categories:
        cur.execute("INSERT OR IGNORE INTO categories (category_name, description) VALUES (?, ?)", 
                   (category_name, description))
    
    # Create admin user if it doesn't exist
    cur.execute("INSERT OR IGNORE INTO users (username, password, email) VALUES (?, ?, ?)",
                ('admin_user', 'admin123', 'admin@unfake.com'))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database schema created/updated successfully!")
    print("Default categories and admin user have been set up.")
    print("You can now run the application.")

if __name__ == "__main__":
    create_schema()
