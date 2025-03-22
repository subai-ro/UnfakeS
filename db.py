# db.py
import sqlite3
import os

# For ML
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import pickle

_model_pipeline = None

def get_connection():
    db_path = os.path.join(os.getcwd(), "unfake.db")  # Ensures DB is in the working directory
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def check_user_credentials(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return (row is not None) and (row['password'] == password)

def get_user_id(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row['user_id'] if row else None

def register_user(username, password, email):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, password, email, join_date, profile_picture, bio)
            VALUES (?, ?, ?, DATE('now'), '', '')
        """, (username, password, email))
        conn.commit()
        return True
    except Exception as e:
        print("Error registering user:", e)
        return False
    finally:
        conn.close()

def get_all_articles():
    """
    Return the articles, including ml_score, source_link, etc.
    """
    conn = get_connection()
    cur = conn.cursor()
    sql = """
    SELECT a.article_id,
           a.title,
           a.overall_rating,
           a.is_fake,
           a.submitter_id,
           IFNULL(u.username, 'Unknown') AS submitter_name,
           group_concat(c.category_name, ', ') AS category_list,
           a.ml_score,
           a.source_link
    FROM articles a
    LEFT JOIN users u ON a.submitter_id = u.user_id
    LEFT JOIN article_category ac ON a.article_id = ac.article_id
    LEFT JOIN categories c ON ac.category_id = c.category_id
    GROUP BY a.article_id
    ORDER BY a.article_id
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_article_as_fake(article_id, fake=True):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE articles SET is_fake=? WHERE article_id=?", (1 if fake else 0, article_id))
    conn.commit()
    conn.close()

def rate_article(user_id, article_id, rating_value, comment):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ratings (user_id, article_id, rating_value, comment)
        VALUES (?, ?, ?, ?)
    """, (user_id, article_id, rating_value, comment))
    conn.commit()
    conn.close()

def get_top_3_users():
    conn = get_connection()
    cur = conn.cursor()
    sql = """
    SELECT u.username,
           COUNT(r.rating_id) AS total_ratings
    FROM users u
    JOIN ratings r ON u.user_id = r.user_id
    GROUP BY u.username
    ORDER BY total_ratings DESC
    LIMIT 3
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_low_credibility_articles():
    """
    Now that we updated the view:
    This shows is_fake=1 AND overall_rating >= 3.
    """
    conn = get_connection()
    cur = conn.cursor()
    sql = """
    SELECT article_id, title, author_name, overall_rating
    FROM v_low_credibility
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT category_id, category_name
    FROM categories
    ORDER BY category_name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def insert_article_category(article_id, category_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO article_category (article_id, category_id)
        VALUES (?, ?)
    """, (article_id, category_id))
    conn.commit()
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

def ml_analyze_article(text, link=""):
    global _model_pipeline
    if _model_pipeline is None:
        load_or_train_ml_model()

    combined = text + " " + link
    prob_real = _model_pipeline.predict_proba([combined])[0][1]
    ml_score = round(prob_real * 5, 2)
    return ml_score

def update_ml_score(article_id, ml_score):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE articles SET ml_score=? WHERE article_id=?", (ml_score, article_id))
    conn.commit()
    conn.close()

# ============ SEARCH FUNCTION ============

def search_articles_db(category=None, min_rating=None, publication_date=None, username=None):
    """
    Dynamic search based on provided filters.
    """
    conn = get_connection()
    cur = conn.cursor()

    base_sql = """
    SELECT DISTINCT a.article_id,
           a.title,
           a.overall_rating,
           a.is_fake,
           a.submitter_id,
           IFNULL(u.username, 'Unknown') AS submitter_name,
           group_concat(c.category_name, ', ') AS category_list,
           a.ml_score,
           a.source_link,
           a.publication_date
    FROM articles a
    LEFT JOIN users u ON a.submitter_id = u.user_id
    LEFT JOIN article_category ac ON a.article_id = ac.article_id
    LEFT JOIN categories c ON ac.category_id = c.category_id
    WHERE 1=1
    """
    params = []
    if category:
        base_sql += " AND c.category_name = ?"
        params.append(category)
    if min_rating:
        base_sql += " AND a.overall_rating >= ?"
        params.append(min_rating)
    if publication_date:
        base_sql += " AND a.publication_date = ?"
        params.append(publication_date)
    if username:
        base_sql += " AND u.username = ?"
        params.append(username)

    base_sql += " GROUP BY a.article_id ORDER BY a.article_id"

    cur.execute(base_sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ CATEGORY MANAGEMENT ============

def add_category(category_name, description=""):
    """
    Adds a new category. Returns True if added, False if it already exists.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO categories (category_name, description)
            VALUES (?, ?)
        """, (category_name, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Category already exists
        return False
    finally:
        conn.close()

def remove_category(category_id):
    """
    Removes a category by its ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM categories
        WHERE category_id = ?
    """, (category_id,))
    conn.commit()
    conn.close()

# ============ ARTICLE MANAGEMENT ============

def remove_article(article_id):
    """
    Removes an article by its ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM articles
        WHERE article_id = ?
    """, (article_id,))
    conn.commit()
    conn.close()
