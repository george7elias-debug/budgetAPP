import io
import base64
from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)

# ----- Data Models -----
class Transaction:
    _id_counter = 1
    def __init__(self, amount, date, recurring=False, interval_days=0):
        self.id = Transaction._id_counter
        Transaction._id_counter += 1
        self.amount = amount
        self.date = date
        self.recurring = recurring
        self.interval_days = interval_days

class BudgetApp:
    def __init__(self):
        self.incomes = []
        self.expenses = []

    # --- Add/Edit/Remove ---
    def add_income(self, amount, date, recurring=False, interval_days=0):
        self.incomes.append(Transaction(amount, date, recurring, interval_days))

    def add_expense(self, amount, date, recurring=False, interval_days=0):
        self.expenses.append(Transaction(amount, date, recurring, interval_days))

    def remove_transaction(self, t_id, type_):
        if type_ == 'income':
            self.incomes = [t for t in self.incomes if t.id != t_id]
        else:
            self.expenses = [t for t in self.expenses if t.id != t_id]

    def edit_transaction(self, t_id, type_, amount, date, recurring=False, interval_days=0):
        lst = self.incomes if type_ == 'income' else self.expenses
        for t in lst:
            if t.id == t_id:
                t.amount = amount
                t.date = date
                t.recurring = recurring
                t.interval_days = interval_days
                break

    # --- Forecast ---
    def generate_balance_forecast(self, days_ahead=365*3):
        today = datetime.today().date()
        end_date = today + timedelta(days=days_ahead)
        balance_by_date = {today + timedelta(n): 0 for n in range(days_ahead + 1)}

        # Apply incomes
        for inc in self.incomes:
            date = inc.date
            while date <= end_date:
                if date >= today:
                    balance_by_date[date] += inc.amount
                if inc.recurring:
                    date += timedelta(days=inc.interval_days)
                else:
                    break

        # Apply expenses
        for exp in self.expenses:
            date = exp.date
            while date <= end_date:
                if date >= today:
                    balance_by_date[date] -= exp.amount
                if exp.recurring:
                    date += timedelta(days=exp.interval_days)
                else:
                    break

        # Sorted net balances
        dates_sorted = sorted(balance_by_date.keys())
        balances = []
        net = 0
        for d in dates_sorted:
            net += balance_by_date[d]
            balances.append(net)
        return dates_sorted, balances

    # --- Plot ---
    def generate_plot(self):
        dates, balances = self.generate_balance_forecast()
        fig = go.Figure()

        # Plot net balance
        fig.add_trace(go.Scatter(
            x=dates,
            y=balances,
            mode='lines+markers',
            name='Net Balance',
            line=dict(color='blue')
        ))

        fig.update_layout(
            title='Net Balance Forecast (1 Year)',
            xaxis_title='Date',
            yaxis_title='Net Balance',
            xaxis=dict(rangeslider=dict(visible=True)),
            yaxis=dict(autorange=True),
            template='plotly_white'
        )

        return pio.to_html(fig, full_html=False)

budget = BudgetApp()

# ----- HTML Template -----
html_template = """
<!DOCTYPE html>
<html>
<head><title>Budget App</title></head>
<body>
<h1>Budget Tracker</h1>

<h2>Add Income</h2>
<form method="POST" action="/">
    <input type="hidden" name="action" value="add_income">
    <label>Amount:</label><input name="income" type="number" step="0.01" required><br>
    <label>Date:</label><input name="income_date" type="date" required><br>
    <label>Recurring:</label>
    <select name="income_recurring">
        <option value="no">One-Time</option>
        <option value="yes">Recurring</option>
    </select><br>
    <label>Interval Days:</label><input name="income_interval" type="number"><br>
    <button type="submit">Add Income</button>
</form>

<h2>Add Expense</h2>
<form method="POST" action="/">
    <input type="hidden" name="action" value="add_expense">
    <label>Amount:</label><input name="expense" type="number" step="0.01" required><br>
    <label>Date:</label><input name="expense_date" type="date" required><br>
    <label>Recurring:</label>
    <select name="expense_recurring">
        <option value="no">One-Time</option>
        <option value="yes">Recurring</option>
    </select><br>
    <label>Interval Days:</label><input name="expense_interval" type="number"><br>
    <button type="submit">Add Expense</button>
</form>

<hr>
<h2>Incomes</h2>
<table border="1">
<tr><th>Amount</th><th>Date</th><th>Recurring</th><th>Interval</th><th>Action</th></tr>
{% for t in incomes %}
<tr>
<td>{{ t.amount }}</td>
<td>{{ t.date }}</td>
<td>{{ 'Yes' if t.recurring else 'No' }}</td>
<td>{{ t.interval_days }}</td>
<td>
    <a href="/remove/income/{{ t.id }}">Remove</a>
</td>
</tr>
{% endfor %}
</table>

<h2>Expenses</h2>
<table border="1">
<tr><th>Amount</th><th>Date</th><th>Recurring</th><th>Interval</th><th>Action</th></tr>
{% for t in expenses %}
<tr>
<td>{{ t.amount }}</td>
<td>{{ t.date }}</td>
<td>{{ 'Yes' if t.recurring else 'No' }}</td>
<td>{{ t.interval_days }}</td>
<td>
    <a href="/remove/expense/{{ t.id }}">Remove</a>
</td>
</tr>
{% endfor %}
</table>

<hr>
<h2>Net Balance Forecast</h2>
{{ plot | safe }}

</body>
</html>
"""

# ----- Routes -----
@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_income':
            amt = float(request.form['income'])
            date_obj = datetime.strptime(request.form['income_date'], "%Y-%m-%d").date()
            recurring = request.form.get('income_recurring') == 'yes'
            interval = int(request.form['income_interval']) if request.form.get('income_interval') else 0
            budget.add_income(amt, date_obj, recurring, interval)
        elif action == 'add_expense':
            amt = float(request.form['expense'])
            date_obj = datetime.strptime(request.form['expense_date'], "%Y-%m-%d").date()
            recurring = request.form.get('expense_recurring') == 'yes'
            interval = int(request.form['expense_interval']) if request.form.get('expense_interval') else 0
            budget.add_expense(amt, date_obj, recurring, interval)
        return redirect(url_for('index'))

    plot = budget.generate_plot()
    return render_template_string(html_template, incomes=budget.incomes, expenses=budget.expenses, plot=plot)

@app.route('/remove/<type_>/<int:t_id>')
def remove_transaction(type_, t_id):
    budget.remove_transaction(t_id, type_)
    return redirect(url_for('index'))

# ----- Run App -----
if __name__ == '__main__':
    app.run(debug=True)
