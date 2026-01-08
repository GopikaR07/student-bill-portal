import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

print("REQUESTS TABLE:")
for r in cur.execute("SELECT * FROM requests"):
    print(r)

print("\nSTUDENTS TABLE:")
for s in cur.execute("SELECT * FROM students"):
    print(s)

db.close()
