import csv
import re
import sqlite3
from datetime import date
from pathlib import Path
from .models import PlatformError
from . import llm

SCHEMA = 'dept_budgets(Department TEXT, Fiscal_Year INTEGER, Quarter TEXT, Allocated_Budget REAL, Actual_Spend REAL); currency INR'


def connect(csv_path: Path):
    db = sqlite3.connect(':memory:')
    try:
        db.execute('CREATE TABLE dept_budgets(Department TEXT, Fiscal_Year INTEGER, Quarter TEXT, Allocated_Budget REAL, Actual_Spend REAL)')
        with csv_path.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        db.executemany('INSERT INTO dept_budgets VALUES (?, ?, ?, ?, ?)',
                       [(r['Department'], int(r['Fiscal_Year']), r['Quarter'], float(r['Allocated_Budget']), float(r['Actual_Spend'])) for r in rows])
        db.commit()
        db.execute('PRAGMA query_only=ON')
        # Even model-generated queries cannot read another table, write, attach, or use file functions.
        def authorize(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and arg1 == 'dept_budgets':
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() in {'sum', 'avg', 'min', 'max', 'count', 'round', 'abs', 'coalesce'}:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        db.set_authorizer(authorize)
        steps = [0]
        def progress():
            steps[0] += 1
            return int(steps[0] > 10000)
        db.set_progress_handler(progress, 100)
        return db
    except Exception:
        db.close()
        raise PlatformError('Cannot load the budget data. Restore samples/budget.csv with the documented columns.') from None


def plan(question: str, today=None):
    q = question.lower()
    if re.search(r'\b(delete|drop|update|insert|alter|attach|pragma)\b', q):
        raise PlatformError('Budget access is read-only. Ask a question about allocation, spending or overspend.')
    years = re.findall(r'\b20\d{2}\b', q)
    quarters = re.findall(r'\bq[1-4]\b', q)
    clauses, params = [], []
    if 'this quarter' in q:
        today = today or date.today()
        years = [str(today.year)]
        quarters = [f'q{(today.month - 1) // 3 + 1}']
    if len(set(years)) > 1 or len(set(quarters)) > 1 or re.search(r'\b(last|previous|next)\b', q):
        raise PlatformError('In local mode, specify one year and one quarter, for example Q2 2025. Multi-period comparisons require the optional model backend.')
    if years:
        clauses.append('Fiscal_Year = ?'); params.append(int(years[0]))
    if quarters:
        clauses.append('Quarter = ?'); params.append(quarters[0].upper())
    departments = ['Marketing', 'Sales', 'Engineering', 'HR', 'Finance', 'Operations']
    matches = [d for d in departments if re.search(r'\b' + d.lower() + r'\b', q)]
    if matches:
        clauses.append('Department IN (' + ','.join('?' for _ in matches) + ')'); params.extend(matches)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    if re.search(r'overspent|overspend|exceed|over budget', q):
        sql = 'SELECT Department, SUM(Allocated_Budget) AS Allocated_Budget, SUM(Actual_Spend) AS Actual_Spend, ROUND(SUM(Actual_Spend)-SUM(Allocated_Budget), 2) AS Overspend FROM dept_budgets' + where
        sql += ' GROUP BY Department HAVING SUM(Actual_Spend)>SUM(Allocated_Budget) ORDER BY Overspend DESC'
        if re.search(r'\b(most|highest|largest)\b', q):
            sql += ' LIMIT 1'
    elif 'average' in q:
        sql = 'SELECT Department, Quarter, ROUND(AVG(Actual_Spend), 2) AS Average_Spend FROM dept_budgets' + where + ' GROUP BY Department, Quarter ORDER BY Quarter, Department'
    elif re.search(r'\b(total|sum)\b', q):
        column = 'Allocated_Budget' if 'allocat' in q else 'Actual_Spend'
        sql = f'SELECT ROUND(SUM({column}), 2) AS Total FROM dept_budgets' + where
    elif re.search(r'allocat|budget|spend|spent|department', q):
        sql = 'SELECT Department, Fiscal_Year, Quarter, Allocated_Budget, Actual_Spend FROM dept_budgets' + where
        sql += ' ORDER BY Actual_Spend DESC' if re.search(r'sort|highest|most|descending', q) else ' ORDER BY Fiscal_Year, Quarter, Department'
    else:
        raise PlatformError('Please ask a budget allocation, total spending, average spending or overspend question.')
    return sql, params


def execute_readonly(db, sql, params=()):
    if not re.match(r'^\s*SELECT\b', sql, re.I) or ';' in sql.rstrip().rstrip(';'):
        raise PlatformError('The SQL proposal was rejected: only one read-only SELECT is allowed.')
    try:
        cursor = db.execute(sql, params)
        rows = cursor.fetchmany(201)
        return [dict(zip([d[0] for d in cursor.description], r)) for r in rows[:200]], len(rows) > 200
    except sqlite3.Error:
        raise PlatformError('The SQL query was rejected or could not run. Rephrase using the budget columns and a specific quarter/year.') from None


def answer(question, csv_path):
    if llm.enabled():
        sql = llm.complete('Return only one SQLite SELECT for this schema: ' + SCHEMA + '. Never write data. No markdown. Current date: ' + str(date.today()), question).strip()
        params = []
    else:
        sql, params = plan(question)
    db = connect(csv_path)
    try:
        rows, truncated = execute_readonly(db, sql, params)
    finally:
        db.close()
    if not rows or all(v is None for row in rows for v in row.values()):
        response = 'No matching budget records/results. The sample covers Q1–Q4 2025 and 2026. Try Q2 2025.'
    else:
        response = f'Budget query returned {len(rows)} row(s). All amounts are INR.'
        if truncated:
            response += ' Showing the first 200 rows.'
    return response, {'rows': rows, 'sql': sql, 'parameters': params, 'currency': 'INR', 'truncated': truncated}
