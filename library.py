"""Library management logic. Everything that touches the database lives here.

server.py only turns HTTP requests into calls to these functions.
The rules (loan length, loan limit, fines) are the constants just below.
"""
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

LOAN_DAYS = 14        # how long a book can be kept
MAX_LOANS = 3         # books one member can have out at the same time
FINE_PER_DAY = 0.50   # fine for each day a book is overdue
CURRENCY = '$'        # shown next to fines in the app

HERE = Path(__file__).parent
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class LibraryError(Exception):
    """A problem the user can fix. `status` is the HTTP status code to send."""
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---------- database ----------

def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(db_path, reset=False):
    """Create the database from schema.sql and seed.sql the first time (or when reset=True)."""
    path = Path(db_path)
    if reset and path.exists():
        path.unlink()
    fresh = not path.exists()
    conn = connect(db_path)
    if fresh:
        conn.executescript((HERE / 'schema.sql').read_text(encoding='utf-8'))
        conn.executescript((HERE / 'seed.sql').read_text(encoding='utf-8'))
        conn.commit()
    conn.close()


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _today():
    return date.today().isoformat()


def _money(value):
    return round(float(value) + 1e-9, 2)


# ---------- validation helpers ----------

def _text(data, key, label, required=True, max_len=120):
    value = str(data.get(key) or '').strip()
    if required and not value:
        raise LibraryError(f'{label} is required.')
    if len(value) > max_len:
        raise LibraryError(f'{label} must be {max_len} characters or fewer.')
    return value


def _copies(data):
    try:
        copies = int(data.get('copies', 1))
    except (TypeError, ValueError):
        raise LibraryError('Copies must be a whole number.')
    if not 1 <= copies <= 50:
        raise LibraryError('Copies must be between 1 and 50.')
    return copies


# ---------- config and stats ----------

def config():
    return {'loan_days': LOAN_DAYS, 'max_loans': MAX_LOANS, 'fine_per_day': FINE_PER_DAY, 'currency': CURRENCY}


def stats(conn):
    totals = _one(conn, '''
        SELECT (SELECT COUNT(*)              FROM books)   AS titles,
               (SELECT COALESCE(SUM(copies),0) FROM books) AS copies,
               (SELECT COUNT(*)              FROM members WHERE status = 'active') AS members,
               (SELECT COUNT(*) FROM loans WHERE returned_on IS NULL)                         AS active_loans,
               (SELECT COUNT(*) FROM loans WHERE returned_on IS NULL AND due_on < date('now', 'localtime')) AS overdue_loans,
               (SELECT COALESCE(SUM(CAST(julianday(date('now', 'localtime')) - julianday(due_on) AS INTEGER)), 0)
                  FROM loans WHERE returned_on IS NULL AND due_on < date('now', 'localtime'))              AS overdue_days,
               (SELECT COALESCE(SUM(fine), 0) FROM loans WHERE fine_paid = 0)                 AS unpaid_fines
    ''')
    totals['available_copies'] = totals['copies'] - totals['active_loans']
    totals['fines_due'] = _money(totals.pop('unpaid_fines') + totals.pop('overdue_days') * FINE_PER_DAY)
    totals['by_category'] = _rows(conn, 'SELECT category, COUNT(*) AS titles FROM books GROUP BY category ORDER BY titles DESC, category')
    return totals


# ---------- books ----------

def list_books(conn, q='', category='', only_available=False):
    sql, params = 'SELECT * FROM v_book_availability WHERE 1=1', []
    if q:
        like = f'%{q.strip()}%'
        sql += " AND (title LIKE ? OR author LIKE ? OR COALESCE(isbn, '') LIKE ? OR category LIKE ?)"
        params += [like] * 4
    if category:
        sql += ' AND category = ?'
        params.append(category)
    if only_available:
        sql += ' AND available > 0'
    return _rows(conn, sql + ' ORDER BY title COLLATE NOCASE', params)


def get_book(conn, book_id):
    book = _one(conn, 'SELECT * FROM v_book_availability WHERE book_id = ?', (book_id,))
    if not book:
        raise LibraryError('Book not found.', 404)
    return book


def _book_fields(data):
    return (_text(data, 'title', 'Title'), _text(data, 'author', 'Author'),
            _text(data, 'isbn', 'ISBN', required=False, max_len=20) or None,
            _text(data, 'category', 'Category', required=False, max_len=40) or 'General', _copies(data))


def add_book(conn, data):
    title, author, isbn, category, copies = _book_fields(data)
    cur = conn.execute('INSERT INTO books (title, author, isbn, category, copies) VALUES (?, ?, ?, ?, ?)',
                       (title, author, isbn, category, copies))
    conn.commit()
    return get_book(conn, cur.lastrowid)


def update_book(conn, book_id, data):
    current = get_book(conn, book_id)
    title, author, isbn, category, copies = _book_fields(data)
    on_loan = current['copies'] - current['available']
    if copies < on_loan:
        raise LibraryError(f'{on_loan} copies are on loan, so there must be at least {on_loan} copies.', 409)
    conn.execute('UPDATE books SET title=?, author=?, isbn=?, category=?, copies=? WHERE book_id=?',
                 (title, author, isbn, category, copies, book_id))
    conn.commit()
    return get_book(conn, book_id)


def delete_book(conn, book_id):
    book = get_book(conn, book_id)
    if book['copies'] - book['available'] > 0:
        raise LibraryError('This book is on loan. Return it before deleting it.', 409)
    conn.execute('DELETE FROM books WHERE book_id = ?', (book_id,))
    conn.commit()


# ---------- members ----------

_MEMBER_SQL = '''
    SELECT m.*,
      (SELECT COUNT(*) FROM loans WHERE member_id = m.member_id AND returned_on IS NULL) AS active_loans,
      (SELECT COUNT(*) FROM loans WHERE member_id = m.member_id AND returned_on IS NULL AND due_on < date('now', 'localtime')) AS overdue_loans,
      (SELECT COALESCE(SUM(fine), 0) FROM loans WHERE member_id = m.member_id AND fine_paid = 0) AS unpaid_fines,
      (SELECT COALESCE(SUM(CAST(julianday(date('now', 'localtime')) - julianday(due_on) AS INTEGER)), 0)
         FROM loans WHERE member_id = m.member_id AND returned_on IS NULL AND due_on < date('now', 'localtime')) AS overdue_days
    FROM members m
'''


def _member_row(row):
    row['fines_due'] = _money(row.pop('unpaid_fines') + row.pop('overdue_days') * FINE_PER_DAY)
    return row


def list_members(conn, q=''):
    sql, params = _MEMBER_SQL + ' WHERE 1=1', []
    if q:
        sql += ' AND (m.name LIKE ? OR m.email LIKE ?)'
        params += [f'%{q.strip()}%'] * 2
    return [_member_row(r) for r in _rows(conn, sql + ' ORDER BY m.name COLLATE NOCASE', params)]


def get_member(conn, member_id):
    row = _one(conn, _MEMBER_SQL + ' WHERE m.member_id = ?', (member_id,))
    if not row:
        raise LibraryError('Member not found.', 404)
    return _member_row(row)


def add_member(conn, data):
    name = _text(data, 'name', 'Name', max_len=80)
    email = _text(data, 'email', 'Email', max_len=120).lower()
    if not EMAIL_RE.match(email):
        raise LibraryError('Enter a valid email address.')
    phone = _text(data, 'phone', 'Phone', required=False, max_len=30) or None
    try:
        cur = conn.execute('INSERT INTO members (name, email, phone, joined_on) VALUES (?, ?, ?, ?)',
                           (name, email, phone, _today()))
    except sqlite3.IntegrityError:
        raise LibraryError('A member with that email already exists.', 409)
    conn.commit()
    return get_member(conn, cur.lastrowid)


def update_member(conn, member_id, data):
    current = get_member(conn, member_id)
    name = _text(data, 'name', 'Name', max_len=80) if 'name' in data else current['name']
    phone = (_text(data, 'phone', 'Phone', required=False, max_len=30) or None) if 'phone' in data else current['phone']
    status = data.get('status', current['status'])
    if status not in ('active', 'suspended'):
        raise LibraryError('Status must be active or suspended.')
    conn.execute('UPDATE members SET name=?, phone=?, status=? WHERE member_id=?', (name, phone, status, member_id))
    conn.commit()
    return get_member(conn, member_id)


# ---------- loans ----------

def _loan_row(row):
    row['fine_due'] = _money(row['days_overdue'] * FINE_PER_DAY if row['state'] != 'returned' else row['fine'])
    return row


def list_loans(conn, status='all', member_id=None, book_id=None):
    sql, params = 'SELECT * FROM v_loans WHERE 1=1', []
    if status == 'active':       # everything still out, including overdue
        sql += ' AND returned_on IS NULL'
    elif status in ('overdue', 'returned'):
        sql += ' AND state = ?'
        params.append(status)
    if member_id:
        sql += ' AND member_id = ?'
        params.append(member_id)
    if book_id:
        sql += ' AND book_id = ?'
        params.append(book_id)
    sql += ' ORDER BY (returned_on IS NOT NULL), CASE WHEN returned_on IS NULL THEN due_on END, returned_on DESC, loan_id DESC'
    return [_loan_row(r) for r in _rows(conn, sql, params)]


def get_loan(conn, loan_id):
    row = _one(conn, 'SELECT * FROM v_loans WHERE loan_id = ?', (loan_id,))
    if not row:
        raise LibraryError('Loan not found.', 404)
    return _loan_row(row)


def borrow(conn, book_id, member_id):
    """Issue a book. The checks run in the order a librarian would think of them."""
    book = get_book(conn, book_id)
    member = get_member(conn, member_id)
    if member['status'] != 'active':
        raise LibraryError(f"{member['name']}'s membership is suspended.", 409)
    if member['overdue_loans']:
        raise LibraryError(f"{member['name']} has an overdue book. It must be returned first.", 409)
    if member['active_loans'] >= MAX_LOANS:
        raise LibraryError(f"{member['name']} already has {MAX_LOANS} books out, which is the limit.", 409)
    if _one(conn, 'SELECT 1 FROM loans WHERE book_id=? AND member_id=? AND returned_on IS NULL', (book_id, member_id)):
        raise LibraryError(f"{member['name']} already has this book.", 409)
    if book['available'] < 1:
        raise LibraryError(f"No copies of {book['title']} are available right now.", 409)
    today = date.today()
    cur = conn.execute('INSERT INTO loans (book_id, member_id, borrowed_on, due_on) VALUES (?, ?, ?, ?)',
                       (book_id, member_id, today.isoformat(), (today + timedelta(days=LOAN_DAYS)).isoformat()))
    conn.commit()
    return get_loan(conn, cur.lastrowid)


def return_loan(conn, loan_id):
    loan = get_loan(conn, loan_id)
    if loan['returned_on']:
        raise LibraryError('This book has already been returned.', 409)
    fine = _money(loan['days_overdue'] * FINE_PER_DAY)
    conn.execute('UPDATE loans SET returned_on = ?, fine = ? WHERE loan_id = ?', (_today(), fine, loan_id))
    conn.commit()
    return get_loan(conn, loan_id)


def pay_fine(conn, loan_id):
    loan = get_loan(conn, loan_id)
    if not loan['returned_on']:
        raise LibraryError('Return the book first. The fine is final once it is returned.', 409)
    if loan['fine'] <= 0 or loan['fine_paid']:
        raise LibraryError('There is no unpaid fine on this loan.', 409)
    conn.execute('UPDATE loans SET fine_paid = 1 WHERE loan_id = ?', (loan_id,))
    conn.commit()
    return get_loan(conn, loan_id)
