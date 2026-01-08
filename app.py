from flask import Flask, render_template, request, redirect, send_file
import sqlite3, os
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "uploads/pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()
    cur = db.cursor()

    # CLUBS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        club_name TEXT,
        password TEXT
    )
    """)

    # REQUESTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER,
        total_amount REAL,
        status TEXT
    )
    """)

    # SHOPS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        shop_name TEXT,
        shop_total REAL
    )
    """)

    # BILLS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER,
        bill_no INTEGER,
        bill_amount REAL,
        bill_pdf TEXT
    )
    """)

    # BANK DETAILS  ✅ acc_holder ADDED
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bank_details (
        request_id INTEGER PRIMARY KEY,
        acc_holder TEXT,
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

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["student_id"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        if role == "admin":
            if username == "admin" and password == "admin123":
                return redirect("/admin")
            return "Invalid admin credentials"

        if username != "student":
            return "Invalid username"

        cur.execute("""
            SELECT id FROM clubs
            WHERE username='student' AND password=?
        """, (password,))
        club = cur.fetchone()

        if club:
            return redirect(f"/student/{club[0]}")

        return "Invalid club password"

    return render_template("login.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student/<int:club_id>")
def student_home(club_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT club_name FROM clubs WHERE id=?", (club_id,))
    club_name = cur.fetchone()[0]

    cur.execute("""
        SELECT request_id, total_amount, status
        FROM requests
        WHERE club_id=?
        ORDER BY request_id DESC
    """, (club_id,))
    requests = cur.fetchall()

    return render_template(
        "student_home.html",
        club_id=club_id,
        club_name=club_name,
        requests=requests
    )

# ---------------- NEW REQUEST ----------------
@app.route("/student/<int:club_id>/new", methods=["GET", "POST"])
def student_new(club_id):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()

        cur.execute("""
            INSERT INTO requests (club_id, total_amount, status)
            VALUES (?, ?, 'Pending')
        """, (club_id, request.form["total"]))
        request_id = cur.lastrowid

        passbook = request.files["passbook_pdf"]
        passbook_name = f"{request_id}_passbook.pdf"
        passbook.save(os.path.join(UPLOAD_FOLDER, passbook_name))

        # ✅ acc_holder INSERTED
        cur.execute("""
            INSERT INTO bank_details
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            request.form["acc_holder"],
            request.form["bank"],
            request.form["acc"],
            request.form["ifsc"],
            request.form["branch"],
            f"uploads/pdfs/{passbook_name}"
        ))

        shop_names = request.form.getlist("shop_name[]")
        bill_nos = request.form.getlist("bill_no[]")
        bill_amounts = request.form.getlist("bill_amount[]")
        bill_files = request.files.getlist("bill_pdfs[]")

        shop_map = {}

        for i in range(len(shop_names)):
            shop = shop_names[i]

            if shop not in shop_map:
                cur.execute("""
                    INSERT INTO shops (request_id, shop_name, shop_total)
                    VALUES (?, ?, 0)
                """, (request_id, shop))
                shop_map[shop] = cur.lastrowid

            bill_name = f"{request_id}_{shop}_{bill_nos[i]}.pdf"
            bill_files[i].save(os.path.join(UPLOAD_FOLDER, bill_name))

            cur.execute("""
                INSERT INTO bills (shop_id, bill_no, bill_amount, bill_pdf)
                VALUES (?, ?, ?, ?)
            """, (
                shop_map[shop],
                bill_nos[i],
                bill_amounts[i],
                f"uploads/pdfs/{bill_name}"
            ))

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
        return redirect(f"/student/{club_id}")

    return render_template("student_new.html", club_id=club_id)

# ---------------- STUDENT VIEW ----------------
@app.route("/student/<int:club_id>/view/<int:rid>")
def student_view(club_id, rid):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT club_name FROM clubs WHERE id=?", (club_id,))
    club_name = cur.fetchone()[0]

    cur.execute("""
        SELECT total_amount, status
        FROM requests
        WHERE request_id=? AND club_id=?
    """, (rid, club_id))
    r = cur.fetchone()

    request_data = {
        "id": rid,
        "total": r[0],
        "status": r[1]
    }

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
        """, (s[0],))
        bills = cur.fetchall()

        shops.append({
            "shop_name": s[1],
            "shop_total": s[2],
            "bills": [{
                "bill_no": b[0],
                "bill_amount": b[1],
                "bill_pdf": b[2]
            } for b in bills]
        })

    # ✅ acc_holder FETCHED
    cur.execute("""
        SELECT acc_holder, bank, acc, ifsc, branch, passbook_pdf
        FROM bank_details WHERE request_id=?
    """, (rid,))
    b = cur.fetchone()

    bank = {
        "acc_holder": b[0],
        "bank": b[1],
        "acc": b[2],
        "ifsc": b[3],
        "branch": b[4],
        "passbook_pdf": b[5]
    }

    return render_template(
        "student_view.html",
        club_id=club_id,
        club_name=club_name,
        request=request_data,
        shops=shops,
        bank=bank
    )

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT r.request_id, c.club_name,
               r.total_amount, r.status
        FROM requests r
        JOIN clubs c ON r.club_id = c.id
        ORDER BY r.request_id DESC
    """)
    reqs = cur.fetchall()

    rows = []

    for r in reqs:
        request_id = r[0]

        cur.execute("""
            SELECT shop_id, shop_name, shop_total
            FROM shops WHERE request_id=?
        """, (request_id,))
        shops_raw = cur.fetchall()

        shops = []
        for s in shops_raw:
            cur.execute("""
                SELECT bill_no, bill_amount, bill_pdf
                FROM bills WHERE shop_id=?
            """, (s[0],))
            bills = cur.fetchall()

            shops.append({
                "shop_name": s[1],
                "shop_total": s[2],
                "bills": bills
            })

        # ✅ acc_holder INCLUDED
        cur.execute("""
            SELECT acc_holder, bank, acc, ifsc, branch, passbook_pdf
            FROM bank_details WHERE request_id=?
        """, (request_id,))
        bank = cur.fetchone()

        rows.append({
            "request_id": request_id,
            "club_name": r[1],
            "total": r[2],
            "status": r[3],
            "shops": shops,
            "bank": bank
        })

    return render_template("admin.html", rows=rows)

@app.route("/verify/<int:rid>/<status>")
def verify(rid, status):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE requests SET status=? WHERE request_id=?", (status, rid))
    db.commit()
    return redirect("/admin")

# ---------------- EXCEL ----------------
@app.route("/download")
def download():
    db = get_db()

    query = """
    SELECT
        c.club_name AS "Club Name",
        
        sh.shop_name AS "Shop",
        b.bill_no AS "Bill No",
        b.bill_amount AS "Bill Amount",
        r.total_amount AS "Total Amount (Club)",
        bd.acc_holder AS "Account Holder Name",
        bd.bank AS "Bank",
        bd.acc AS "Account No",
        bd.ifsc AS "IFSC",
        bd.branch AS "Branch",
        r.status AS "Status"
    FROM requests r
    JOIN clubs c ON r.club_id = c.id
    JOIN shops sh ON r.request_id = sh.request_id
    JOIN bills b ON sh.shop_id = b.shop_id
    JOIN bank_details bd ON r.request_id = bd.request_id
    WHERE r.status='Approved'
    ORDER BY c.club_name, sh.shop_name, b.bill_no
    """

    df = pd.read_sql(query, db)
    os.makedirs("excel", exist_ok=True)
    path = "excel/approved_requests.xlsx"
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route("/logout")
def logout():
    return redirect("/")

app.run(debug=True)
