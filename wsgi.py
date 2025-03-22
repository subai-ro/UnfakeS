from app import app
from waitress import serve
from schema_creation import create_schema
import sqlite3
import os

def ensure_admin_exists():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'unfake.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if admin user exists
        cur.execute("SELECT id FROM users WHERE username = 'admin_user'")
        if not cur.fetchone():
            # Create admin user if doesn't exist
            cur.execute("""
                INSERT INTO users (username, password, email)
                VALUES (?, ?, ?)
            """, ('admin_user', 'admin123', 'admin@unfake.com'))
            conn.commit()
            print("Admin user created successfully!")
            print("Username: admin_user")
            print("Password: admin123")
        else:
            print("Admin user already exists")
            
    except Exception as e:
        print(f"Error ensuring admin exists: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Create database schema
    create_schema()
    # Ensure admin user exists
    ensure_admin_exists()
    # Start the server
    serve(app, host='0.0.0.0', port=10000) 