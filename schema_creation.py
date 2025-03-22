# schema_creation.py
import sqlite3

db_path = r"D:\Unfake project\unfake.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1) Create or upgrade tables
create_tables_sql = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT,
    join_date DATE DEFAULT CURRENT_DATE,
    profile_picture TEXT,
    bio TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    article_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    contents TEXT,
    author_name TEXT,
    publication_date DATE,
    overall_rating REAL DEFAULT 0,
    is_fake BOOLEAN DEFAULT 0,
    submitter_id INT,
    ml_score REAL DEFAULT 0,
    source_link TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS article_category (
    article_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (article_id, category_id),
    FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(category_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    rating_value INTEGER NOT NULL,
    comment TEXT,
    rating_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(article_id) REFERENCES articles(article_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_ratings_value ON ratings(rating_value);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);

-- Trigger: Update overall_rating after each new rating
CREATE TRIGGER IF NOT EXISTS trg_update_overall_rating
AFTER INSERT ON ratings
BEGIN
    UPDATE articles
    SET overall_rating = (
        SELECT AVG(r.rating_value)
        FROM ratings r
        WHERE r.article_id = NEW.article_id
    )
    WHERE article_id = NEW.article_id;
END;
"""
cursor.executescript(create_tables_sql)
conn.commit()

# 2) Create or replace the "v_low_credibility" view
cursor.execute("DROP VIEW IF EXISTS v_low_credibility")
cursor.execute("""
CREATE VIEW v_low_credibility AS
SELECT article_id, title, author_name, overall_rating
FROM articles
WHERE is_fake = 1
  AND overall_rating <= 3
""")
conn.commit()

# 3) Clean up duplicate categories
cleanup_duplicates_sql = """
DELETE FROM categories
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM categories
    GROUP BY category_name
);
"""
cursor.execute(cleanup_duplicates_sql)
conn.commit()

print("All core tables + columns verified.")
print("v_low_credibility view created/updated.")
print("Duplicate categories removed.")

conn.close()
print("Schema creation/upgrade complete! Run app.py afterwards.")
