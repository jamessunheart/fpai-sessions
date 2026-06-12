import sqlite3
conn = sqlite3.connect('team_hub.db')
print("Tables:", conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
try:
    print("Invites:", conn.execute("SELECT * FROM invitations").fetchall())
except Exception as e:
    print("Error reading invitations:", e)











