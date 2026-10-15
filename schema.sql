-- Shelfwise library database (SQLite)
-- Three tables (members, books, loans) and two views the app reads from.
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_loans;
DROP VIEW  IF EXISTS v_book_availability;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS members;

CREATE TABLE members (
    member_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    phone     TEXT,
    joined_on TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    status    TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended'))
);

CREATE TABLE books (
    book_id  INTEGER PRIMARY KEY,
    title    TEXT NOT NULL,
    author   TEXT NOT NULL,
    isbn     TEXT,
    category TEXT NOT NULL DEFAULT 'General',
    copies   INTEGER NOT NULL DEFAULT 1 CHECK (copies >= 1)
);

CREATE TABLE loans (
    loan_id     INTEGER PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES books(book_id)     ON DELETE CASCADE,
    member_id   INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    borrowed_on TEXT NOT NULL,                 -- dates are stored as YYYY-MM-DD
    due_on      TEXT NOT NULL,
    returned_on TEXT,                          -- NULL means the book is still out
    fine        REAL    NOT NULL DEFAULT 0,    -- set when the book is returned late
    fine_paid   INTEGER NOT NULL DEFAULT 0 CHECK (fine_paid IN (0, 1))
);

CREATE INDEX idx_loans_book   ON loans(book_id);
CREATE INDEX idx_loans_member ON loans(member_id);
CREATE INDEX idx_loans_open   ON loans(returned_on);

-- Every book with how many copies are free right now.
CREATE VIEW v_book_availability AS
SELECT b.*, b.copies - COUNT(l.loan_id) AS available
FROM books b
LEFT JOIN loans l ON l.book_id = b.book_id AND l.returned_on IS NULL
GROUP BY b.book_id;

-- Every loan with its book, member, and whether it is active, overdue or returned.
CREATE VIEW v_loans AS
SELECT l.*, b.title, b.author, m.name AS member_name,
       CASE WHEN l.returned_on IS NOT NULL THEN 'returned'
            WHEN l.due_on < date('now', 'localtime')    THEN 'overdue'
            ELSE 'active' END AS state,
       CASE WHEN l.returned_on IS NULL AND l.due_on < date('now', 'localtime')
            THEN CAST(julianday(date('now', 'localtime')) - julianday(l.due_on) AS INTEGER)
            ELSE 0 END AS days_overdue
FROM loans l
JOIN books   b ON b.book_id   = l.book_id
JOIN members m ON m.member_id = l.member_id;
