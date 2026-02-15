import sqlite3

con = sqlite3.connect("database.db")

# Удаляем старые таблицы
con.execute("DROP TABLE IF EXISTS news")
con.execute("DROP TABLE IF EXISTS players")
con.execute("DROP TABLE IF EXISTS matches")
con.execute("DROP TABLE IF EXISTS replays")
con.execute("DROP TABLE IF EXISTS teams")
con.execute("DROP TABLE IF EXISTS admins")  # новая таблица

# Создаём новые таблицы
con.execute("""
    CREATE TABLE news (
        id INTEGER PRIMARY KEY,
        title TEXT,
        text TEXT,
        preview_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

con.execute("""
    CREATE TABLE players (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        goals INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        saves INTEGER DEFAULT 0,
        conceded INTEGER DEFAULT 0,
        bio TEXT
    )
""")

con.execute("""
    CREATE TABLE matches (
        id INTEGER PRIMARY KEY,
        team_left_id INTEGER NOT NULL,
        team_right_id INTEGER NOT NULL,
        score TEXT NOT NULL,
        date TEXT NOT NULL,
        result TEXT NOT NULL,
        FOREIGN KEY(team_left_id) REFERENCES teams(id),
        FOREIGN KEY(team_right_id) REFERENCES teams(id)
    )
""")

con.execute("""
    CREATE TABLE replays (
        id INTEGER PRIMARY KEY,
        title TEXT,
        filename TEXT
    )
""")

con.execute("""
    CREATE TABLE teams (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        logo_filename TEXT NOT NULL
    )
""")

con.execute("""
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        totp_secret TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1
    )
""")

# Добавляем первоначального администратора (например, "Main Admin")
# Генерировать секрет будем при первом запуске через код, поэтому пока вставим заглушку,
# но лучше создать через интерфейс. Поэтому оставим таблицу пустой, а первого админа создадим через спец. маршрут.
# Вместо этого при первом запуске, если нет админов, предложим создать главного.

# Добавляем 14 команд
teams_data = [
    ("Eternal Pantheon", "pantheon.png"),
    ("Adjaro Prom", "adjaro.png"),
    ("The Little Outsiders", "outsiders.png"),
    ("Golden Carrots", "carrots.png"),
    ("Underway Luck", "luck.png"),
    ("Deptown Gamblers", "deptown.png"),
    ("PEPElivery Mascots", "mascots.png"),
    ("Okayama Flames", "okayama.png"),
    ("Meteor Msc", "meteor.png"),
    ("Partiya S.O.S.I", "sosi.png"),
    ("CDEK Boosters", "cdek.png"),
    ("Dinamo Mellcity", "dinamo.png"),
    ("Church of Husk", "husk.png"),
    ("Ghosts of the Wasteland", "ghosts.png"),
]

for name, logo in teams_data:
    con.execute("INSERT INTO teams (name, logo_filename) VALUES (?, ?)", (name, logo))

con.commit()