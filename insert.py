import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

cur.execute("INSERT INTO students(student_id) VALUES ('S001')")
cur.execute("INSERT INTO students(student_id) VALUES ('S002')")

db.commit()
db.close()
