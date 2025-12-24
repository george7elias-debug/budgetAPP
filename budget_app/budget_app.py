import sqlite3
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime, timedelta

DB_NAME = "budget.db"
app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            description TEXT,
            amount REAL,
            date TEXT,
            recurring TEXT,
            frequency TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Add transaction
def add_transaction(t_type, description, amount, date, recurring, frequency=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (type, description, amount, date, recurring, frequency) VALUES (?, ?, ?, ?, ?, ?)",
        (t_type, description, amount, date, recurring, frequency)
    )
    conn.commit()
    conn.close()

# Get all transactions
def get_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return data

# Delete transaction
def delete_transaction(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()

# Update transaction
def update_transaction(tx_id, t_type, description, amount, date, recurring, frequency):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE transactions SET type=?, description=?, amount=?, date=?, recurring=?, frequency=? WHERE id=?
    ''', (t_type, description, amount, date, recurring, frequency, tx_id))
    conn.commit()
    conn.close()

# Expand recurring transactions for plotting
def expand_recurring(transactions, start_date=None, end_date=None):
    expanded = []
    if not end_date:
        end_date = datetime.now() + timedelta(days=365*5)
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    for t in transactions:
        t_type, desc, amount, date_str, recurring, freq = t[1], t[2], t[3], t[4], t[5], t[6]
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if recurring == "Recurring" and freq:
            while date <= end_date:
                if not start_date or date >= start_date:
                    expanded.append({"date": date.strftime("%Y-%m-%d"), "type": t_type, "amount": amount})
                if freq == "Weekly":
                    date += timedelta(weeks=1)
                elif freq == "Biweekly":
                    date += timedelta(weeks=2)
                elif freq == "Monthly":
                    month = date.month + 1 if date.month < 12 else 1
                    year = date.year + 1 if month == 1 else date.year
                    day = min(date.day, 28)
                    date = datetime(year, month, day)
                elif freq == "Yearly":
                    date = datetime(date.year + 1, date.month, date.day)
        else:
            if not start_date or date >= start_date:
                expanded.append({"date": date.strftime("%Y-%m-%d"), "type": t_type, "amount": amount})
    return expanded

# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        t_type = request.form["type"]
        desc = request.form["description"]
        amount = float(request.form["amount"])
        date = request.form["date"]
        recurring = request.form["recurring"]
        frequency = request.form.get("frequency") if recurring == "Recurring" else None
        add_transaction(t_type, desc, amount, date, recurring, frequency)
        return redirect(url_for("index"))

    history = get_transactions()
    expanded_transactions = expand_recurring(history)
    return render_template("index.html", history=history, transactions=expanded_transactions)

@app.route("/delete/<int:tx_id>")
def delete(tx_id):
    delete_transaction(tx_id)
    return redirect(url_for("index"))

@app.route("/edit/<int:tx_id>", methods=["GET", "POST"])
def edit(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if request.method == "POST":
        t_type = request.form["type"]
        desc = request.form["description"]
        amount = float(request.form["amount"])
        date = request.form["date"]
        recurring = request.form["recurring"]
        frequency = request.form.get("frequency") if recurring == "Recurring" else None
        update_transaction(tx_id, t_type, desc, amount, date, recurring, frequency)
        return redirect(url_for("index"))
    else:
        c.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
        tx = c.fetchone()
        conn.close()
        return render_template("edit.html", tx=tx)

if __name__ == "__main__":
    app.run(debug=True)
