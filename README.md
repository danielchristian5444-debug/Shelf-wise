# Shelfwise: a library management system

Track books, members, loans and fines from one calm dashboard.

| Layer | Technology | Where |
|---|---|---|
| Pages and layout | HTML, CSS | `web/index.html`, `web/app.html`, `web/css/` |
| Interface | React (loaded from a CDN, no build step) | `web/js/app.js`, `web/js/landing.js` |
| Server and rules | Python 3 (standard library only) | `server.py`, `library.py` |
| Database | SQL (SQLite) | `schema.sql`, `seed.sql`, `queries.sql` |

## Run it

You need Python 3.8 or newer. Nothing else to install.

```
python server.py
```

Open http://localhost:8000. The first run creates `library.db` from `schema.sql` and `seed.sql`.

```
python server.py --port 5000    # another port
python server.py --reset        # rebuild the database with fresh sample data
python -m unittest discover -s tests -v   # run the tests
sqlite3 -header -column library.db < queries.sql   # run the report queries
```

## What it does

- **Dashboard**: titles, free copies, books out, overdue loans, active members and fines due, plus an "attention" list with one-click returns.
- **Books**: search by title, author or category, filter by category or availability, add, edit and delete books.
- **Members**: register readers, see what each has out, suspend and reactivate memberships.
- **Loans**: issue and return books, see due dates and overdue loans, collect fines.

### Rules (change them at the top of `library.py`)

- A loan lasts 14 days (`LOAN_DAYS`).
- A member can have 3 books out at once (`MAX_LOANS`).
- A late book costs 0.50 per day (`FINE_PER_DAY`, shown with `CURRENCY`).
- Members cannot borrow while suspended or while they have an overdue book.
- A book cannot be deleted, or have its copies reduced below the number on loan, while it is out.

## Demo mode (no server)

If the Python server is not running (for example when the `web/` folder is hosted on GitHub Pages), the pages switch to demo mode automatically. A copy of the same rules runs in the browser (`web/js/demo.js`) and data is saved in that browser only. A banner says so, with a button to reset the sample data.

To host the full app with the database, use any Python host (for example PythonAnywhere or Render) and run `server.py` there.

## API

All responses are JSON. Errors look like `{"error": "message"}` with a suitable status (400, 404, 409).

```
GET  /api/config   /api/stats   /api/health
GET  /api/books?q=&category=&available=1      POST /api/books      PUT, DELETE /api/books/<id>
GET  /api/members?q=                          POST /api/members    PUT /api/members/<id>
GET  /api/loans?status=active|overdue|returned|all&member_id=
POST /api/loans {book_id, member_id}
POST /api/loans/<id>/return        POST /api/loans/<id>/pay
```

## Design and usability notes

- Landing page and app share one visual system: sage background, white rounded frame, dark pill buttons, one orange accent.
- Every action gives feedback: toasts for success and errors, clear reasons when a loan is blocked (before you press the button), skeletons while loading, helpful empty states.
- Destructive actions (delete a book, suspend a member) ask for confirmation.
- Keyboard: skip link, visible focus rings, dialogs trap focus and close with Esc, press `/` to jump to search.
- Phones: bottom tab bar, tables turn into cards, tap targets are at least 36px, no sideways scrolling.
- Respects "reduce motion". Colour is never the only signal: status chips always carry text.

## Files

```
server.py  library.py          Python server and rules
schema.sql  seed.sql  queries.sql   SQL
tests/test_library.py          unit and API tests
web/index.html                 landing page
web/app.html                   the app
web/css/  web/js/  web/img/    styles, scripts, artwork
```

Sample data only. The names are made up.
