from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

# ----------------------
# Database setup
# ----------------------
DB_NAME = os.path.join(app.root_path, "budget.db")

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
            recurring TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup (works with Gunicorn/Render)
init_db()

# ----------------------
# Database helpers
# ----------------------
def get_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_transaction(t_type, description, amount, date, recurring):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (type, description, amount, date, recurring) VALUES (?, ?, ?, ?, ?)",
              (t_type, description, amount, date, recurring))
    conn.commit()
    conn.close()

def delete_transaction(tx_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()

def update_transaction(tx_id, t_type, description, amount, date, recurring):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE transactions
        SET type=?, description=?, amount=?, date=?, recurring=?
        WHERE id=?
    """, (t_type, description, amount, date, recurring, tx_id))
    conn.commit()
    conn.close()

# ----------------------
# Routes
# ----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        t_type = request.form["type"]
        description = request.form["description"]
        amount = float(request.form["amount"])
        date = request.form["date"]
        recurring = request.form["recurring"]
        add_transaction(t_type, description, amount, date, recurring)
        return redirect(url_for("index"))

    # Fetch history and prepare for table/chart
    history = get_history()
    return render_template("index.html", history=history)

@app.route("/delete/<int:tx_id>")
def delete(tx_id):
    delete_transaction(tx_id)
    return redirect(url_for("index"))

@app.route("/update/<int:tx_id>", methods=["POST"])
def update(tx_id):
    t_type = request.form["type"]
    description = request.form["description"]
    amount = float(request.form["amount"])
    date = request.form["date"]
    recurring = request.form["recurring"]
    update_transaction(tx_id, t_type, description, amount, date, recurring)
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Local debug
    app.run(debug=True)
