import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

cur.execute("""
INSERT INTO students VALUES
('S001', 'Ria', 'student'),
('S002', 'Henry', 'student')
""")

db.commit()
db.close()
