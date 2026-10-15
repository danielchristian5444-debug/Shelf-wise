-- Report queries. Run them with:  sqlite3 -header -column library.db < queries.sql

-- 1. Overdue loans, longest overdue first (with the fine at 0.50 per day)
SELECT member_name, title, due_on, days_overdue, days_overdue * 0.50 AS fine_due
FROM v_loans
WHERE state = 'overdue'
ORDER BY days_overdue DESC;

-- 2. Books with no free copies right now
SELECT title, author, copies, available
FROM v_book_availability
WHERE available = 0
ORDER BY title;

-- 3. Most borrowed books of all time
SELECT b.title, COUNT(*) AS times_borrowed
FROM loans l
JOIN books b ON b.book_id = l.book_id
GROUP BY b.book_id
ORDER BY times_borrowed DESC, b.title
LIMIT 5;

-- 4. Members and how many books each has out (including members with none)
SELECT m.name, m.status, COUNT(l.loan_id) AS books_out
FROM members m
LEFT JOIN loans l ON l.member_id = m.member_id AND l.returned_on IS NULL
GROUP BY m.member_id
ORDER BY books_out DESC, m.name;

-- 5. Unpaid fines collected so far, by member
SELECT m.name, SUM(l.fine) AS unpaid_fines
FROM loans l
JOIN members m ON m.member_id = l.member_id
WHERE l.fine > 0 AND l.fine_paid = 0
GROUP BY m.member_id;

-- 6. Titles per category
SELECT category, COUNT(*) AS titles, SUM(copies) AS copies
FROM books
GROUP BY category
ORDER BY titles DESC;
