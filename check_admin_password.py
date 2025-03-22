import sqlite3

conn = sqlite3.connect(r"D:\Unfake project\unfake.db")
cur = conn.cursor()

cur.execute("SELECT username, password FROM users WHERE username = 'admin_user'")
row = cur.fetchone()

conn.close()

if row:
    print(f"Admin Password: {row[1]}")
else:
    print("Admin user not found!")
