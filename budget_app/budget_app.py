import sqlite3
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)
DB_NAME = "budget.db"

# -------------------- DATABASE --------------------

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            description TEXT,
            amount REAL,
            date TEXT,
            recurring TEXT,
            frequency TEXT,
            end_date TEXT,
            principal REAL,
            interest_rate REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------- CRUD --------------------

def get_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_transaction(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions
        (type, description, amount, date, recurring, frequency, end_date, principal, interest_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def update_transaction(tx_id, data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE transactions SET
        type=?, description=?, amount=?, date=?, recurring=?, frequency=?, end_date=?, principal=?, interest_rate=?
        WHERE id=?
    """, (*data, tx_id))
    conn.commit()
    conn.close()

def delete_transaction(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()

# -------------------- EXPANSION LOGIC --------------------

def advance_date(date, freq):
    if freq == "Weekly":
        return date + timedelta(weeks=1)
    if freq == "Biweekly":
        return date + timedelta(weeks=2)
    if freq == "Monthly":
        return date + timedelta(days=30)
    if freq == "Yearly":
        return date.replace(year=date.year + 1)
    return date

def expand_transactions(transactions, start=None, end=None):
    expanded = []
    start = datetime.strptime(start, "%Y-%m-%d") if start else None
    end = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now() + timedelta(days=365*10)

    for t in transactions:
        (_, t_type, desc, amt, d, rec, freq, end_date, principal, rate) = t
        date = datetime.strptime(d, "%Y-%m-%d")
        cutoff = datetime.strptime(end_date, "%Y-%m-%d") if end_date else end

        while date <= cutoff:
            if (not start or date >= start) and date <= end:
                amount = amt

                if "Interest" in t_type:
                    period_rate = (rate or 0) / 100
                    amount = (principal or 0) * period_rate
                    if t_type == "Interest Expense":
                        amount *= -1

                expanded.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "type": "Income" if amount >= 0 else "Expense",
                    "amount": abs(amount)
                })

            if rec != "Recurring":
                break
            date = advance_date(date, freq)

    return expanded

# -------------------- ROUTES --------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = (
            request.form["type"],
            request.form["description"],
            float(request.form.get("amount") or 0),
            request.form["date"],
            request.form["recurring"],
            request.form.get("frequency"),
            request.form.get("end_date"),
            request.form.get("principal"),
            request.form.get("interest_rate"),
        )
        add_transaction(data)
        return redirect(url_for("index"))

    history = get_transactions()
    expanded = expand_transactions(history)
    return render_template("index.html", history=history, transactions=expanded)

@app.route("/delete/<int:tx_id>")
def delete(tx_id):
    delete_transaction(tx_id)
    return redirect(url_for("index"))

@app.route("/edit/<int:tx_id>", methods=["GET", "POST"])
def edit(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
        data = (
            request.form["type"],
            request.form["description"],
            float(request.form.get("amount") or 0),
            request.form["date"],
            request.form["recurring"],
            request.form.get("frequency"),
            request.form.get("end_date"),
            request.form.get("principal"),
            request.form.get("interest_rate"),
        )
        update_transaction(tx_id, data)
        return redirect(url_for("index"))

    c.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
    tx = c.fetchone()
    conn.close()
    return render_template("edit.html", tx=tx)

if __name__ == "__main__":
    app.run(debug=True)
