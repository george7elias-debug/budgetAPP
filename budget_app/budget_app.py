import sqlite3
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime, timedelta

DB_NAME = "budget.db"
app = Flask(__name__)

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

def add_transaction(t_type, description, amount, date, recurring, frequency=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (type, description, amount, date, recurring, frequency) VALUES (?, ?, ?, ?, ?, ?)",
              (t_type, description, amount, date, recurring, frequency))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return data

def delete_transaction(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()

def update_transaction(tx_id, t_type, description, amount, date, recurring, frequency):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE transactions SET type=?, description=?, amount=?, date=?, recurring=?, frequency=? WHERE id=?
    ''', (t_type, description, amount, date, recurring, frequency, tx_id))
    conn.commit()
    conn.close()

# Helper to expand recurring transactions for plotting
def expand_recurring(transactions, end_date=None):
    expanded = []
    if not end_date:
        end_date = datetime.now() + timedelta(days=365)  # 1 year ahead
    for t in transactions:
        t_type, desc, amount, date_str, recurring, freq = t[1], t[2], t[3], t[4], t[5], t[6]
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if recurring == "Recurring" and freq:
            while date <= end_date:
                expanded.append({"date": date.strftime("%Y-%m-%d"), "type": t_type, "amount": amount})
                if freq == "Weekly":
                    date += timedelta(weeks=1)
                elif freq == "Monthly":
                    date = datetime(date.year + (date.month // 12), ((date.month % 12) + 1), date.day)
                elif freq == "Yearly":
                    date = datetime(date.year + 1, date.month, date.day)
        else:
            expanded.append({"date": date.strftime("%Y-%m-%d"), "type": t_type, "amount": amount})
    return expanded

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

@app.route("/update/<int:tx_id>", methods=["POST"])
def update(tx_id):
    # For simplicity, just redirect (implement full update form as needed)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
