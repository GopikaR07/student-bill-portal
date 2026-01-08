import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

# Clear existing clubs (safe since new DB)
cur.execute("DELETE FROM clubs")

# Insert clubs
cur.execute("""
INSERT INTO clubs (username, club_name, password)
VALUES
    ('student', 'Club 1', 'club1@psgitech'),
    ('student', 'Club 2', 'club2@psgitech')
""")

db.commit()
db.close()

print("Clubs inserted successfully.")
