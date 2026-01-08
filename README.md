# Student Bill Portal

A Flask-based web application for **clubs** to submit bill reimbursement requests  
and for **admins** to verify, approve, or reject them.

---

## Features

- Club & Admin login
- Single username for clubs (`student`) with different passwords per club
- Multiple shop & bill submission
- PDF upload (Bills & Passbook)
- Bank details submission (including Account Holder Name)
- Request status tracking (Pending / Approved / Rejected)
- Admin approval / rejection
- Excel export of approved requests with full details

---

## Login Details

### Admin Login
- **Username:** admin  
- **Password:** admin123  

### Club Login
- **Username:** student  
- **Passwords:**
  - Club 1 → `club1@psgitech`
  - Club 2 → `club2@psgitech`

> Club name is automatically identified based on the password.

---

## Excel Export (Approved Requests)

The generated Excel file contains the following columns:

1. Club Name  
2. Total Amount (Club)  
3. Account Holder Name  
4. Shop Name  
5. Bill No  
6. Bill Amount  
7. Bank  
8. Account No  
9. IFSC  
10. Branch  
11. Status  

---

## Tech Stack

- Python (Flask)
- SQLite
- HTML, CSS, JavaScript
- Pandas
- Git & GitHub

---

## How to Run

1. Install **Python 3**
2. Install dependencies:
   ```bash
   pip install flask pandas
