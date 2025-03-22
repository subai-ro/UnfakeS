import sqlite3
import os

def check_admin_password():
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'unfake.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT username, password FROM users WHERE username = 'admin_user'")
        row = cur.fetchone()
        
        if row:
            print(f"Admin Username: {row[0]}")
            print(f"Admin Password: {row[1]}")
        else:
            print("Admin user not found!")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_admin_password()
