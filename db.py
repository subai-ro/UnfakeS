# db.py
import sqlite3
import os
import time
from datetime import datetime

# For ML
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import pickle

_model_pipeline = None

def get_connection():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'unfake.db')
    
    # Add retry logic for database connections
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=20)  # Increased timeout
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            return conn
        except sqlite3.OperationalError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise e

def check_user_credentials(username, password):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (username,))
        result = cur.fetchone()
        return result and result['password'] == password
    finally:
        conn.close()

def get_user_id(username):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE username=?", (username,))
        result = cur.fetchone()
        return result['user_id'] if result else None
    finally:
        conn.close()

def register_user(username, password, email):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, password, email)
            VALUES (?, ?, ?)
        """, (username, password, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_articles():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.article_id, a.title, a.contents, a.author_name,
                   a.publication_date, a.overall_rating, a.is_fake,
                   a.submitter_id, u.username as submitter_name,
                   a.ml_score, a.source_link
            FROM articles a
            LEFT JOIN users u ON a.submitter_id = u.user_id
            ORDER BY a.publication_date DESC
        """)
        return cur.fetchall()
    finally:
        conn.close()

def mark_article_as_fake(article_id, is_fake):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles SET is_fake = ? WHERE article_id = ?
        """, (is_fake, article_id))
        conn.commit()
    finally:
        conn.close()

def rate_article(user_id, article_id, rating_value, comment=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ratings (user_id, article_id, rating_value, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, article_id, rating_value, comment))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_top_3_users():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.username, COUNT(r.rating_id) as rating_count
            FROM users u
            JOIN ratings r ON u.user_id = r.user_id
            GROUP BY u.user_id
            ORDER BY rating_count DESC
            LIMIT 3
        """)
        return cur.fetchall()
    finally:
        conn.close()

def get_low_credibility_articles():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM v_low_credibility
            ORDER BY publication_date DESC
        """)
        return cur.fetchall()
    finally:
        conn.close()

def get_categories():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
        return cur.fetchall()
    finally:
        conn.close()

def insert_article_category(article_id, category_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO article_category (article_id, category_id)
            VALUES (?, ?)
        """, (article_id, category_id))
        conn.commit()
    finally:
        conn.close()

# ============ MACHINE LEARNING STUFF ============

def load_or_train_ml_model():
    global _model_pipeline
    model_file = "ml_model.pkl"

    if os.path.exists(model_file):
        with open(model_file, "rb") as f:
            _model_pipeline = pickle.load(f)
        return

    data = [
        ("Breaking news about economy stocks soared", 1),
        ("Click here for cheap pills guaranteed miracle", 0),
        ("Local election updates show new policies", 1),
        ("Win big money with one trick", 0),
        ("Technology advances with new AI model", 1),
        ("Gossip about celebrities unbelievable secret", 0)
    ]
    texts = [d[0] for d in data]
    labels = [d[1] for d in data]

    vec = TfidfVectorizer()
    clf = LogisticRegression()
    _model_pipeline = Pipeline([
        ("tfidf", vec),
        ("clf", clf)
    ])
    _model_pipeline.fit(texts, labels)

    with open(model_file, "wb") as f:
        pickle.dump(_model_pipeline, f)

def ml_analyze_article(contents, source_link):
    # Placeholder for ML analysis
    return 0.5

def update_ml_score(article_id, score):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles SET ml_score = ? WHERE article_id = ?
        """, (score, article_id))
        conn.commit()
    finally:
        conn.close()

# ============ SEARCH FUNCTION ============

def search_articles_db(category=None, min_rating=None, publication_date=None, username=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT DISTINCT a.article_id, a.title, a.contents, a.author_name,
                   a.publication_date, a.overall_rating, a.is_fake,
                   a.submitter_id, u.username as submitter_name,
                   a.ml_score, a.source_link
            FROM articles a
            LEFT JOIN users u ON a.submitter_id = u.user_id
            LEFT JOIN article_category ac ON a.article_id = ac.article_id
            LEFT JOIN categories c ON ac.category_id = c.category_id
            WHERE 1=1
        """
        params = []
        
        if category:
            query += " AND c.category_name = ?"
            params.append(category)
        if min_rating:
            query += " AND a.overall_rating >= ?"
            params.append(float(min_rating))
        if publication_date:
            query += " AND DATE(a.publication_date) = DATE(?)"
            params.append(publication_date)
        if username:
            query += " AND u.username = ?"
            params.append(username)
            
        query += " ORDER BY a.publication_date DESC"
        
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()

# ============ CATEGORY MANAGEMENT ============

def add_category(category_name, description=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categories (category_name, description)
            VALUES (?, ?)
        """, (category_name, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_category(category_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        conn.commit()
    finally:
        conn.close()

# ============ ARTICLE MANAGEMENT ============

def remove_article(article_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM articles WHERE article_id = ?", (article_id,))
        conn.commit()
    finally:
        conn.close()

def update_password(username, new_password):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET password = ? WHERE username = ?
        """, (new_password, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        conn.close()

def create_article(title, contents, author_name, source_link, submitter_id, categories):
    """
    Create a new article with categories in a single transaction.
    Returns the article_id if successful, None if failed.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Insert article
        cur.execute("""
            INSERT INTO articles (title, contents, author_name, source_link, submitter_id)
            VALUES (?, ?, ?, ?, ?)
        """, (title, contents, author_name, source_link, submitter_id))
        
        article_id = cur.lastrowid
        
        # Insert categories
        for category_id in categories:
            cur.execute("""
                INSERT INTO article_category (article_id, category_id)
                VALUES (?, ?)
            """, (article_id, category_id))
        
        # Run ML analysis and update score
        score = ml_analyze_article(contents, source_link)
        cur.execute("""
            UPDATE articles SET ml_score = ? WHERE article_id = ?
        """, (score, article_id))
        
        conn.commit()
        return article_id
    except Exception as e:
        conn.rollback()
        print(f"Error submitting article: {e}")
        return None
    finally:
        conn.close()
