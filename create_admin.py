import sqlite3
import os

def create_admin_user():
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'unfake.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if admin user already exists
        cur.execute("SELECT id FROM users WHERE username = 'admin_user'")
        if cur.fetchone():
            print("Admin user already exists!")
            return
        
        # Create admin user
        cur.execute("""
            INSERT INTO users (username, password, email)
            VALUES (?, ?, ?)
        """, ('admin_user', 'admin123', 'admin@unfake.com'))
        
        conn.commit()
        print("Admin user created successfully!")
        print("Username: admin_user")
        print("Password: admin123")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_admin_user() 