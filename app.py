# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from db import (
    check_user_credentials,
    get_user_id,
    get_all_articles,
    rate_article,
    mark_article_as_fake,
    get_connection,
    get_top_3_users,
    get_low_credibility_articles,
    register_user,
    get_categories,
    insert_article_category,
    ml_analyze_article,
    update_ml_score,
    search_articles_db,
    add_category,
    remove_category,
    remove_article,
    update_password,
    create_article
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Make sure to set this in Render's environment variables

# Configure for production
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_user_credentials(username, password):
            session['username'] = username
            flash("Login successful!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Try again.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    user = session['username']
    articles = get_all_articles()

    # gather comments
    conn = get_connection()
    cur = conn.cursor()
    comments_dict = {}
    for art in articles:
        article_id = art['article_id']
        cur.execute("""
            SELECT r.comment, r.rating_value, r.user_id, u.username
            FROM ratings r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.article_id = ?
        """, (article_id,))
        these_comments = cur.fetchall()
        comments_dict[article_id] = these_comments
    conn.close()

    return render_template('dashboard.html',
                           username=user,
                           articles=articles,
                           comments_dict=comments_dict)

@app.route('/rate', methods=['POST'])
def rate():
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    user_id = get_user_id(session['username'])
    article_id = request.form.get('article_id')

    conn = get_connection()
    cur = conn.cursor()
    # check if user already rated
    cur.execute("SELECT rating_id FROM ratings WHERE user_id=? AND article_id=?", (user_id, article_id))
    existing = cur.fetchone()
    if existing:
        flash("You have already rated this article!")
        conn.close()
        return redirect(url_for('dashboard'))

    rating_value = request.form.get('rating_value')
    comment = request.form.get('comment', "")
    cur.execute("""
        INSERT INTO ratings (user_id, article_id, rating_value, comment)
        VALUES (?, ?, ?, ?)
    """, (user_id, article_id, rating_value, comment))
    conn.commit()
    conn.close()

    flash(f"Article {article_id} rated {rating_value}!")
    return redirect(url_for('dashboard'))

@app.route('/admin/mark_fake', methods=['POST'])
def admin_mark_fake():
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    article_id = request.form.get('article_id')
    mark_article_as_fake(article_id, True)
    flash(f"Article {article_id} marked as fake.")
    return redirect(url_for('dashboard'))

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.article_id, a.title, a.contents, a.author_name,
               a.publication_date, a.overall_rating, a.is_fake,
               a.submitter_id, IFNULL(u.username,'Unknown') AS submitter_name,
               a.ml_score, a.source_link
        FROM articles a
        LEFT JOIN users u ON a.submitter_id = u.user_id
        WHERE a.article_id = ?
    """, (article_id,))
    article = cur.fetchone()

    cur.execute("""
        SELECT c.category_name
        FROM categories c
        JOIN article_category ac ON c.category_id = ac.category_id
        WHERE ac.article_id = ?
    """, (article_id,))
    categories = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT r.rating_value, r.comment, r.user_id, u.username, r.rating_date
        FROM ratings r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.article_id = ?
        ORDER BY r.rating_date DESC
    """, (article_id,))
    ratings_list = cur.fetchall()

    conn.close()
    return render_template('article_detail.html',
                           article=article,
                           categories=categories,
                           ratings_list=ratings_list)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, username, email, join_date, profile_picture, bio
        FROM users
        WHERE user_id=?
    """, (user_id,))
    user = cur.fetchone()

    cur.execute("""
        SELECT a.article_id, a.title, r.rating_value, r.comment, r.rating_date
        FROM ratings r
        JOIN articles a ON r.article_id = a.article_id
        WHERE r.user_id = ?
        ORDER BY r.rating_date DESC
    """, (user_id,))
    rated_articles = cur.fetchall()

    conn.close()
    return render_template('user_profile.html',
                           user=user,
                           rated_articles=rated_articles,
                           user_id=user_id)

@app.route('/edit_profile/<int:user_id>', methods=['GET','POST'])
def edit_profile(user_id):
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            new_bio = request.form.get('bio', '')
            file = request.files.get('profile_pic')
            pic_path = ''
            
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    pic_path = os.path.join('static', 'uploads', f"user_{user_id}_{filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], f"user_{user_id}_{filename}"))
                else:
                    flash("Invalid file type. Allowed types: png, jpg, jpeg, gif")
                    return redirect(url_for('edit_profile', user_id=user_id))

            sql = "UPDATE users SET bio=?, profile_picture=? WHERE user_id=?"
            cur.execute(sql, (new_bio, pic_path, user_id))
            conn.commit()
            flash("Profile updated successfully.")
            return redirect(url_for('user_profile', user_id=user_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating profile: {str(e)}")
            return redirect(url_for('edit_profile', user_id=user_id))
        finally:
            conn.close()

    try:
        cur.execute("SELECT bio, profile_picture FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return render_template('edit_profile.html', 
                             user_id=user_id, 
                             existing_bio=row['bio'] if row else '', 
                             existing_pic=row['profile_picture'] if row else '')
    except Exception as e:
        flash(f"Error loading profile: {str(e)}")
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

@app.route('/admin', methods=['GET','POST'])
def admin_panel():
    if 'username' not in session or session['username'] != 'admin_user':
        flash("Admin only.")
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        # Handle Removing Articles
        if 'remove_article_id' in request.form:
            article_id = request.form['remove_article_id']
            # Optional: Confirm the article exists before deleting
            cur.execute("SELECT title FROM articles WHERE article_id=?", (article_id,))
            article = cur.fetchone()
            if article:
                remove_article(article_id)
                flash(f"Article '{article['title']}' (ID: {article_id}) deleted.")
            else:
                flash("Article not found.")

        # Handle Marking Articles as Real
        elif 'mark_real_id' in request.form:
            article_id = request.form['mark_real_id']
            cur.execute("SELECT title FROM articles WHERE article_id=?", (article_id,))
            article = cur.fetchone()
            if article:
                mark_article_as_fake(article_id, False)
                flash(f"Article '{article['title']}' (ID: {article_id}) marked as real.")
            else:
                flash("Article not found.")

        # Handle Removing Users
        elif 'remove_user_id' in request.form:
            remove_id = request.form['remove_user_id']
            cur.execute("SELECT username FROM users WHERE user_id=?", (remove_id,))
            user = cur.fetchone()
            if user:
                remove_user(remove_id)  # You need to define this function similar to remove_article
                flash(f"User '{user['username']}' (ID: {remove_id}) removed.")
            else:
                flash("User not found.")

        # Handle Adding New Categories
        elif 'new_category' in request.form:
            new_cat = request.form['new_category'].strip()
            description = request.form.get('new_category_description', '').strip()
            if new_cat:
                success = add_category(new_cat, description)
                if success:
                    flash(f"Category '{new_cat}' added.")
                else:
                    flash(f"Category '{new_cat}' already exists.")
            else:
                flash("Category name cannot be empty.")

        # Handle Removing Categories
        elif 'remove_category_id' in request.form:
            category_id = request.form['remove_category_id']
            cur.execute("SELECT category_name FROM categories WHERE category_id=?", (category_id,))
            category = cur.fetchone()
            if category:
                remove_category(category_id)
                flash(f"Category '{category['category_name']}' removed.")
            else:
                flash("Category not found.")

    # Fetch articles, users, and categories
    cur.execute("SELECT article_id, title, is_fake FROM articles ORDER BY article_id")
    articles_list = cur.fetchall()

    cur.execute("SELECT user_id, username FROM users ORDER BY user_id")
    users_list = cur.fetchall()

    cur.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
    categories_list = cur.fetchall()

    conn.close()
    return render_template(
        'admin.html',
        articles=articles_list,
        users=users_list,
        categories=categories_list
    )

@app.route('/search', methods=['GET'])
def search_articles():
    # We'll call the dynamic search function from db
    from db import search_articles_db
    cat = request.args.get('category', None)
    min_rating = request.args.get('min_rating', None)
    date = request.args.get('publication_date', None)
    username = request.args.get('username', None)

    # If user used the search form, we pass these values:
    results = search_articles_db(category=cat, min_rating=min_rating,
                                 publication_date=date, username=username)
    return render_template('search.html', results=results)

@app.route('/top_raters')
def top_raters():
    top3 = get_top_3_users()
    return render_template('top_raters.html', top3=top3)

@app.route('/low_credibility')
def low_credibility():
    rows = get_low_credibility_articles()
    return render_template('low_credibility.html', articles=rows)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        success = register_user(username, password, email)
        if success:
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        else:
            flash("Registration failed. Username might already exist.")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/submit_article', methods=['GET', 'POST'])
def submit_article():
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            contents = request.form.get('contents')
            author_name = request.form.get('author_name', session['username'])
            source_link = request.form.get('source_link', '')
            categories = request.form.getlist('categories')
            
            if not all([title, contents]):
                flash("Please fill in all required fields.")
                return redirect(url_for('submit_article'))

            # Get user ID
            user_id = get_user_id(session['username'])
            if not user_id:
                flash("Error: User not found.")
                return redirect(url_for('login'))

            # Create article using the renamed function
            article_id = create_article(
                title=title,
                contents=contents,
                author_name=author_name,
                source_link=source_link,
                submitter_id=user_id,
                categories=categories
            )

            if article_id:
                flash("Article submitted successfully!")
                return redirect(url_for('dashboard'))
            else:
                flash("Error submitting article. Please try again.")
                return redirect(url_for('submit_article'))

        except Exception as e:
            flash(f"Error submitting article: {str(e)}")
            return redirect(url_for('submit_article'))

    categories = get_categories()
    return render_template('submit_article.html', categories=categories)

# Add a route for the user to quickly jump to their own profile from the nav:
@app.route('/my_profile')
def my_profile():
    if 'username' not in session:
        flash("Please log in.")
        return redirect(url_for('login'))
    uid = get_user_id(session['username'])
    return redirect(url_for('user_profile', user_id=uid))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        flash("Please login first!")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not check_user_credentials(session['username'], current_password):
            flash("Current password is incorrect!")
            return redirect(url_for('change_password'))
            
        if new_password != confirm_password:
            flash("New passwords do not match!")
            return redirect(url_for('change_password'))
            
        if update_password(session['username'], new_password):
            flash("Password updated successfully!")
            return redirect(url_for('dashboard'))
        else:
            flash("Error updating password!")
            
    return render_template('change_password.html')

if __name__ == '__main__':
    app.run(debug=True)
