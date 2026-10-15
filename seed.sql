-- Sample data. Loan dates are relative to today, so some loans are always overdue.
INSERT INTO books (book_id, title, author, category, copies) VALUES
    (1,  'Things Fall Apart',                  'Chinua Achebe',                       'Fiction',    3),
    (2,  'Half of a Yellow Sun',               'Chimamanda Ngozi Adichie',            'Fiction',    2),
    (3,  'Python Crash Course',                'Eric Matthes',                        'Technology', 2),
    (4,  'Clean Code',                         'Robert C. Martin',                    'Technology', 1),
    (5,  'Eloquent JavaScript',                'Marijn Haverbeke',                    'Technology', 2),
    (6,  'Database Design for Mere Mortals',   'Michael J. Hernandez',                'Technology', 1),
    (7,  'The Pragmatic Programmer',           'Andrew Hunt and David Thomas',        'Technology', 2),
    (8,  'A Brief History of Time',            'Stephen Hawking',                     'Science',    2),
    (9,  'Cosmos',                             'Carl Sagan',                          'Science',    1),
    (10, 'The Selfish Gene',                   'Richard Dawkins',                     'Science',    1),
    (11, 'Sapiens',                            'Yuval Noah Harari',                   'History',    2),
    (12, 'Long Walk to Freedom',               'Nelson Mandela',                      'Biography',  2),
    (13, 'Born a Crime',                       'Trevor Noah',                         'Biography',  1),
    (14, 'Educated',                           'Tara Westover',                       'Biography',  1),
    (15, 'Americanah',                         'Chimamanda Ngozi Adichie',            'Fiction',    2),
    (16, '1984',                               'George Orwell',                       'Fiction',    3),
    (17, 'Pride and Prejudice',                'Jane Austen',                         'Fiction',    2),
    (18, 'The Alchemist',                      'Paulo Coelho',                        'Fiction',    2),
    (19, 'Atomic Habits',                      'James Clear',                         'Self-Help',  2),
    (20, 'Head First HTML and CSS',            'Elisabeth Robson and Eric Freeman',   'Technology', 1),
    (21, 'Learning React',                     'Alex Banks and Eve Porcello',         'Technology', 1),
    (22, 'SQL in 10 Minutes',                  'Ben Forta',                           'Technology', 2),
    (23, 'The Great Gatsby',                   'F. Scott Fitzgerald',                 'Fiction',    2),
    (24, 'Guns, Germs, and Steel',             'Jared Diamond',                       'History',    1);

INSERT INTO members (member_id, name, email, phone, joined_on, status) VALUES
    (1,  'Amina Bello',    'amina.bello@example.com',    '0801 000 0001', date('now', 'localtime', '-400 days'), 'active'),
    (2,  'Tunde Adeyemi',  'tunde.adeyemi@example.com',  '0801 000 0002', date('now', 'localtime', '-380 days'), 'active'),
    (3,  'Chidi Okafor',   'chidi.okafor@example.com',   '0801 000 0003', date('now', 'localtime', '-300 days'), 'active'),
    (4,  'Zainab Musa',    'zainab.musa@example.com',    '0801 000 0004', date('now', 'localtime', '-260 days'), 'active'),
    (5,  'Ngozi Eze',      'ngozi.eze@example.com',      '0801 000 0005', date('now', 'localtime', '-210 days'), 'active'),
    (6,  'Ibrahim Sule',   'ibrahim.sule@example.com',   '0801 000 0006', date('now', 'localtime', '-190 days'), 'active'),
    (7,  'Funke Ade',      'funke.ade@example.com',      '0801 000 0007', date('now', 'localtime', '-150 days'), 'active'),
    (8,  'Emeka Obi',      'emeka.obi@example.com',      '0801 000 0008', date('now', 'localtime', '-120 days'), 'suspended'),
    (9,  'Halima Yusuf',   'halima.yusuf@example.com',   '0801 000 0009', date('now', 'localtime', '-90 days'),  'active'),
    (10, 'David Etim',     'david.etim@example.com',     '0801 000 0010', date('now', 'localtime', '-45 days'),  'active');

-- loan_id, book, member, borrowed, due, returned, fine, fine_paid
INSERT INTO loans (loan_id, book_id, member_id, borrowed_on, due_on, returned_on, fine, fine_paid) VALUES
    -- returned loans (history)
    (1,  3,  1,  date('now', 'localtime', '-40 days'), date('now', 'localtime', '-26 days'), date('now', 'localtime', '-28 days'), 0,   0),
    (2,  1,  2,  date('now', 'localtime', '-35 days'), date('now', 'localtime', '-21 days'), date('now', 'localtime', '-18 days'), 1.5, 0),
    (3,  12, 3,  date('now', 'localtime', '-30 days'), date('now', 'localtime', '-16 days'), date('now', 'localtime', '-17 days'), 0,   0),
    (4,  16, 4,  date('now', 'localtime', '-25 days'), date('now', 'localtime', '-11 days'), date('now', 'localtime', '-9 days'),  1.0, 1),
    (5,  7,  9,  date('now', 'localtime', '-50 days'), date('now', 'localtime', '-36 days'), date('now', 'localtime', '-37 days'), 0,   0),
    -- active loans, not yet due
    (6,  5,  1,  date('now', 'localtime', '-5 days'),  date('now', 'localtime', '+9 days'),  NULL, 0, 0),
    (7,  2,  1,  date('now', 'localtime', '-2 days'),  date('now', 'localtime', '+12 days'), NULL, 0, 0),
    (8,  14, 5,  date('now', 'localtime', '-10 days'), date('now', 'localtime', '+4 days'),  NULL, 0, 0),
    (9,  8,  6,  date('now', 'localtime', '-12 days'), date('now', 'localtime', '+2 days'),  NULL, 0, 0),
    (10, 20, 7,  date('now', 'localtime', '-3 days'),  date('now', 'localtime', '+11 days'), NULL, 0, 0),
    (11, 9,  10, date('now', 'localtime', '-1 days'),  date('now', 'localtime', '+13 days'), NULL, 0, 0),
    -- overdue loans
    (12, 4,  2,  date('now', 'localtime', '-24 days'), date('now', 'localtime', '-10 days'), NULL, 0, 0),
    (13, 11, 3,  date('now', 'localtime', '-20 days'), date('now', 'localtime', '-6 days'),  NULL, 0, 0),
    (14, 22, 4,  date('now', 'localtime', '-17 days'), date('now', 'localtime', '-3 days'),  NULL, 0, 0),
    (15, 6,  9,  date('now', 'localtime', '-30 days'), date('now', 'localtime', '-16 days'), NULL, 0, 0);
