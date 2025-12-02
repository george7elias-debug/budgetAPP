from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)
DB_NAME = "budget.db"

# ----------------------
# Database helpers
# ----------------------
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

def add_transaction(type_, desc, amount, date, recurring):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (type, description, amount, date, recurring) VALUES (?, ?, ?, ?, ?)",
        (type_, desc, amount, date, recurring)
    )
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def remove_transaction(t_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (t_id,))
    conn.commit()
    conn.close()

def get_transaction(t_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE id=?", (t_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_transaction(t_id, type_, desc, amount, date, recurring):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE transactions
        SET type=?, description=?, amount=?, date=?, recurring=?
        WHERE id=?
    """, (type_, desc, amount, date, recurring, t_id))
    conn.commit()
    conn.close()

# ----------------------
# Routes
# ----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        type_ = request.form['type']
        desc = request.form['description']
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0
        date = request.form['date']
        recurring = request.form['recurring']
        add_transaction(type_, desc, amount, date, recurring)
        return redirect(url_for('index'))

    history = get_history()
    return render_template("index.html", history=history)

@app.route('/remove/<int:t_id>')
def remove(t_id):
    remove_transaction(t_id)
    return redirect(url_for('index'))

# ----------------------
# Inline update route
# ----------------------
@app.route('/update', methods=['POST'])
def update_inline():
    data = request.get_json()
    t_id = data.get('id')
    field = data.get('field')
    value = data.get('value')

    allowed_fields = ['type', 'description', 'amount', 'date', 'recurring']
    if field not in allowed_fields:
        return jsonify({'status': 'error', 'message': 'Invalid field'})

    # Validation
    if field == 'amount':
        try:
            value = float(value)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Amount must be numeric'})
    elif field == 'type' and value not in ['income', 'expense']:
        return jsonify({'status': 'error', 'message': 'Type must be income or expense'})
    elif field == 'recurring' and value not in ['one-time', 'recurring']:
        return jsonify({'status': 'error', 'message': 'Recurring must be one-time or recurring'})
    elif field == 'date':
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format'})

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f"UPDATE transactions SET {field}=? WHERE id=?", (value, t_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# ----------------------
# Chart data route
# ----------------------
@app.route('/chart-data')
def chart_data():
    history = get_history()
    df = pd.DataFrame(history, columns=['id', 'type', 'description', 'amount', 'date', 'recurring'])
    if df.empty:
        return jsonify({'dates': [], 'cumulative': []})
    
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values('date', inplace=True)
    df['net'] = df.apply(lambda row: row['amount'] if row['type']=='income' else -row['amount'], axis=1)
    df['cumulative'] = df['net'].cumsum()
    dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
    cumulative = df['cumulative'].tolist()
    
    return jsonify({'dates': dates, 'cumulative': cumulative})

# ----------------------
# Main
# ----------------------
if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
