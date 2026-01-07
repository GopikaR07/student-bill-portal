from flask import Flask, render_template, request, redirect, send_file
import sqlite3, os
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS students(
        student_id TEXT PRIMARY KEY,
        password TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        shop TEXT,
        product_name TEXT,
        total REAL,
        bank TEXT,
        acc TEXT,
        ifsc TEXT,
        branch TEXT,
        status TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        file_name TEXT
    )""")

    db.commit()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        sid = request.form["student_id"]
        pwd = request.form["password"]

        db = get_db()
        cur = db.cursor()

        if role == "admin":
            if sid == "admin" and pwd == "admin":
                return redirect("/admin")
            return "Invalid admin credentials"

        cur.execute("SELECT student_id FROM students WHERE student_id=?", (sid,))
        if not cur.fetchone():
            return "Student ID not found"

        if pwd == "student":
            return redirect(f"/student/{sid}")

        return "Invalid student password"

    return render_template("login.html")

# ---------- STUDENT HOME ----------
@app.route("/student/<sid>")
def student_home(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, total, status FROM requests WHERE student_id=? ORDER BY id DESC",
        (sid,)
    )
    data = cur.fetchall()
    return render_template("student_home.html", sid=sid, requests=data)

# ---------- STUDENT NEW ----------
@app.route("/student/<sid>/new", methods=["GET","POST"])
def student_new(sid):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()

        names = request.form.getlist("product_name[]")
        prices = request.form.getlist("product_price[]")
        products = "; ".join([f"{n} : {p}" for n, p in zip(names, prices)])

        cur.execute("""
            INSERT INTO requests
            (student_id, shop, product_name, total, bank, acc, ifsc, branch, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            sid,
            request.form["shop"],
            products,
            request.form["total"],
            request.form["bank"],
            request.form["acc"],
            request.form["ifsc"],
            request.form["branch"]
        ))

        req_id = cur.lastrowid

        # BILL PDF
        # BILL PDF
        bill = request.files["bill_pdf"]
        if bill:
            fname = f"{req_id}_bill.pdf"
            bill.save(os.path.join(UPLOAD_FOLDER, fname))
            cur.execute(
                "INSERT INTO documents VALUES (NULL, ?, ?)",
                (req_id, f"uploads/pdfs/{fname}")
            )

        # PASSBOOK PDF
        passbook = request.files["passbook_pdf"]
        if passbook:
            fname = f"{req_id}_passbook.pdf"
            passbook.save(os.path.join(UPLOAD_FOLDER, fname))
            cur.execute(
                "INSERT INTO documents VALUES (NULL, ?, ?)",
                (req_id, f"uploads/pdfs/{fname}")
            )


        db.commit()
        return redirect(f"/student/{sid}")

    return render_template("student_new.html", sid=sid)

# ---------- ADMIN ----------
@app.route("/admin")
def admin():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT id, student_id, shop, product_name, total, status
        FROM requests ORDER BY id DESC
    """)
    reqs = cur.fetchall()

    rows = []
    for r in reqs:
        cur.execute(
            "SELECT file_path FROM documents WHERE request_id=?",
            (r[0],)
        )
        files = cur.fetchall()

        bill = passbook = ""
        for f in files:
            if "bill" in f[0]:
                bill = f[0]
            elif "passbook" in f[0]:
                passbook = f[0]

        rows.append({
            "id": r[0],
            "student_id": r[1],
            "shop": r[2],
            "products": r[3],
            "total": r[4],
            "status": r[5],
            "bill": bill,
            "passbook": passbook
        })

    return render_template("admin.html", rows=rows)

@app.route("/verify/<int:rid>/<status>")
def verify(rid, status):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE requests SET status=? WHERE id=?", (status, rid))
    db.commit()
    return redirect("/admin")

@app.route("/download")
def download():
    db = get_db()
    df = pd.read_sql("SELECT * FROM requests WHERE status='Approved'", db)
    os.makedirs("excel", exist_ok=True)
    path = "excel/approved.xlsx"
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route("/uploads/pdfs/<filename>")
def view_pdf(filename):
    return send_file(os.path.join("uploads/pdfs", filename))

@app.route("/logout")
def logout():
    return redirect("/")

app.run(debug=True)
