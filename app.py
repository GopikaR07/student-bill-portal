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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        student_id TEXT PRIMARY KEY,
        student_name TEXT,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests(
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        total_amount REAL,
        status TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shops(
        shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        shop_name TEXT,
        shop_total REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills(
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER,
        bill_no INTEGER,
        bill_amount REAL,
        bill_pdf TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bank_details(
        request_id INTEGER PRIMARY KEY,
        bank TEXT,
        acc TEXT,
        ifsc TEXT,
        branch TEXT,
        passbook_pdf TEXT
    )
    """)

    db.commit()
    db.close()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        uid = request.form["student_id"]
        pwd = request.form["password"]

        db = get_db()
        cur = db.cursor()

        if role == "admin":
            if uid == "admin" and pwd == "admin":
                return redirect("/admin")
            return "Invalid admin credentials"

        cur.execute(
            "SELECT * FROM students WHERE student_id=? AND password=?",
            (uid, pwd)
        )
        if cur.fetchone():
            return redirect(f"/student/{uid}")

        return "Invalid student credentials"

    return render_template("login.html")

# ---------- STUDENT HOME ----------

@app.route("/student/<sid>")
def student_home(sid):
    db = get_db()
    cur = db.cursor()

    # Student name
    cur.execute(
        "SELECT student_name FROM students WHERE student_id=?",
        (sid,)
    )
    row = cur.fetchone()
    student_name = row[0] if row else ""

    # Requests
    cur.execute("""
        SELECT request_id, total_amount, status
        FROM requests
        WHERE student_id=?
        ORDER BY request_id DESC
    """, (sid,))
    requests = cur.fetchall()

    print("DEBUG SID:", sid)
    print("DEBUG REQUESTS:", requests)

    return render_template(
        "student_home.html",
        sid=sid,
        student_name=student_name,
        requests=requests
    )

# ---------- STUDENT NEW ----------
@app.route("/student/<sid>/new", methods=["GET","POST"])
def student_new(sid):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()

        # CREATE REQUEST
        cur.execute("""
            INSERT INTO requests(student_id, total_amount, status)
            VALUES (?, ?, 'Pending')
        """, (sid, request.form["total"]))
        request_id = cur.lastrowid

        # BANK DETAILS
        passbook = request.files["passbook_pdf"]
        passbook_name = f"{request_id}_passbook.pdf"
        passbook.save(os.path.join(UPLOAD_FOLDER, passbook_name))

        cur.execute("""
            INSERT INTO bank_details
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            request.form["bank"],
            request.form["acc"],
            request.form["ifsc"],
            request.form["branch"],
            f"uploads/pdfs/{passbook_name}"
        ))

        # BILL DATA
        shop_names = request.form.getlist("shop_name[]")
        bill_nos = request.form.getlist("bill_no[]")
        bill_amounts = request.form.getlist("bill_amount[]")
        bill_files = request.files.getlist("bill_pdfs[]")

        shop_map = {}

        for i in range(len(shop_names)):
            shop = shop_names[i]

            if shop not in shop_map:
                cur.execute("""
                    INSERT INTO shops(request_id, shop_name, shop_total)
                    VALUES (?, ?, 0)
                """, (request_id, shop))
                shop_map[shop] = cur.lastrowid

            bill_file = bill_files[i]
            bill_name = f"{request_id}_{shop}_{bill_nos[i]}.pdf"
            bill_file.save(os.path.join(UPLOAD_FOLDER, bill_name))

            cur.execute("""
                INSERT INTO bills
                (shop_id, bill_no, bill_amount, bill_pdf)
                VALUES (?, ?, ?, ?)
            """, (
                shop_map[shop],
                bill_nos[i],
                bill_amounts[i],
                f"uploads/pdfs/{bill_name}"
            ))

        # UPDATE SHOP TOTALS
        for shop_id in shop_map.values():
            cur.execute("""
                UPDATE shops
                SET shop_total = (
                    SELECT SUM(bill_amount)
                    FROM bills WHERE shop_id=?
                )
                WHERE shop_id=?
            """, (shop_id, shop_id))

        db.commit()
        db.close()
        return redirect(f"/student/{sid}")

    return render_template("student_new.html", sid=sid)

# ---------- ADMIN ----------

@app.route("/admin")
def admin():
    db = get_db()
    cur = db.cursor()

    # Get requests with student info
    cur.execute("""
        SELECT r.request_id, s.student_id, s.student_name,
               r.total_amount, r.status
        FROM requests r
        JOIN students s ON r.student_id = s.student_id
        ORDER BY r.request_id DESC
    """)
    reqs = cur.fetchall()

    rows = []

    for r in reqs:
        request_id = r[0]

        # Shops
        cur.execute("""
            SELECT shop_id, shop_name, shop_total
            FROM shops
            WHERE request_id=?
        """, (request_id,))
        shops = cur.fetchall()

        shop_data = []
        for s in shops:
            shop_id = s[0]

            # Bills per shop
            cur.execute("""
                SELECT bill_no, bill_amount, bill_pdf
                FROM bills
                WHERE shop_id=?
                ORDER BY bill_no
            """, (shop_id,))
            bills = cur.fetchall()

            shop_data.append({
                "shop_name": s[1],
                "shop_total": s[2],
                "bills": bills
            })

        # Bank details
        cur.execute("""
            SELECT bank, acc, ifsc, branch, passbook_pdf
            FROM bank_details
            WHERE request_id=?
        """, (request_id,))
        bank = cur.fetchone()

        rows.append({
            "request_id": request_id,
            "student_id": r[1],
            "student_name": r[2],
            "total": r[3],
            "status": r[4],
            "shops": shop_data,
            "bank": bank
        })

    return render_template("admin.html", rows=rows)

@app.route("/verify/<int:rid>/<status>")
def verify(rid, status):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE requests SET status=? WHERE request_id=?",
        (status, rid)
    )
    db.commit()
    return redirect("/admin")

@app.route("/uploads/pdfs/<filename>")
def view_pdf(filename):
    return send_file(os.path.join("uploads/pdfs", filename))

@app.route("/download")
def download():
    db = get_db()
    df = pd.read_sql("""
        SELECT s.student_id, s.student_name,
               r.total_amount, r.status
        FROM requests r
        JOIN students s ON r.student_id=s.student_id
        WHERE r.status='Approved'
    """, db)
    os.makedirs("excel", exist_ok=True)
    path = "excel/approved.xlsx"
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route("/logout")
def logout():
    return redirect("/")


@app.route("/student/<sid>/view/<int:rid>")
def student_view(sid, rid):
    db = get_db()
    cur = db.cursor()

    # Student name
    cur.execute(
        "SELECT student_name FROM students WHERE student_id=?",
        (sid,)
    )
    student_name = cur.fetchone()[0]

    # Request info
    cur.execute("""
        SELECT total_amount, status
        FROM requests
        WHERE request_id=? AND student_id=?
    """, (rid, sid))
    r = cur.fetchone()

    request_data = {
        "id": rid,
        "total": r[0],
        "status": r[1]
    }

    # Shops
    cur.execute("""
        SELECT shop_id, shop_name, shop_total
        FROM shops WHERE request_id=?
    """, (rid,))
    shops_raw = cur.fetchall()

    shops = []
    for s in shops_raw:
        cur.execute("""
            SELECT bill_no, bill_amount, bill_pdf
            FROM bills WHERE shop_id=?
            ORDER BY bill_no
        """, (s[0],))
        bills = cur.fetchall()

        shops.append({
            "shop_name": s[1],
            "shop_total": s[2],
            "bills": [
                {
                    "bill_no": b[0],
                    "bill_amount": b[1],
                    "bill_pdf": b[2]
                } for b in bills
            ]
        })

    # Bank details
    cur.execute("""
        SELECT bank, acc, ifsc, branch, passbook_pdf
        FROM bank_details WHERE request_id=?
    """, (rid,))
    b = cur.fetchone()

    bank = {
        "bank": b[0],
        "acc": b[1],
        "ifsc": b[2],
        "branch": b[3],
        "passbook_pdf": b[4]
    }

    return render_template(
        "student_view.html",
        sid=sid,
        student_name=student_name,
        request=request_data,
        shops=shops,
        bank=bank
    )


app.run(debug=True)
