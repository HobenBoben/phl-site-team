from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64

app = Flask(__name__)
app.secret_key = "QCYRI#crhq3cbidihqbccj387r873qyryxqnncqkcshbjdkcQIH@&H"  # В продакшене заменить на случайную строку
app.permanent_session_lifetime = timedelta(minutes=30)

# Пути для данных (монтируются в контейнере)
DB_PATH = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'avi', 'mov', 'mkv', 'zip', 'mcworld', 'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def db():
    return sqlite3.connect(DB_PATH)

# Фильтр для форматирования даты
@app.template_filter('datetime')
def format_datetime(value, format='%d.%m.%Y %H:%M'):
    if value is None:
        return ''
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt.strftime(format)
    except:
        return value

# Фильтр для фото игрока (проверка наличия файла)
@app.template_filter('player_image')
def player_image_filter(name):
    filename = f"{name}.png"
    filepath = os.path.join('images', 'players', filename)
    full_path = os.path.join(app.static_folder, filepath)
    if os.path.isfile(full_path):
        return url_for('static', filename=filepath)
    else:
        return url_for('static', filename='images/players/default.png')

# Инициализация базы данных (создание таблиц, если их нет)
def init_db():
    con = sqlite3.connect(DB_PATH)
    # Проверяем наличие таблицы admins (как индикатор)
    cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
    if cursor.fetchone() is None:
        con.executescript("""
            CREATE TABLE news (
                id INTEGER PRIMARY KEY,
                title TEXT,
                text TEXT,
                preview_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE players (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                conceded INTEGER DEFAULT 0,
                bio TEXT
            );
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY,
                team_left_id INTEGER NOT NULL,
                team_right_id INTEGER NOT NULL,
                score TEXT NOT NULL,
                date TEXT NOT NULL,
                result TEXT NOT NULL,
                FOREIGN KEY(team_left_id) REFERENCES teams(id),
                FOREIGN KEY(team_right_id) REFERENCES teams(id)
            );
            CREATE TABLE replays (
                id INTEGER PRIMARY KEY,
                title TEXT,
                filename TEXT
            );
            CREATE TABLE teams (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                logo_filename TEXT NOT NULL
            );
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                totp_secret TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            );
        """)
        # Добавляем 14 команд (замените названия и файлы логотипов на свои)
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
        print("База данных инициализирована.")
    else:
        print("База данных уже существует.")
    con.close()

# --- Публичные маршруты ---
@app.route("/")
def index():
    con = db()
    news = con.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    con.close()
    return render_template("index.html", news=news)

@app.route("/news")
def news():
    con = db()
    news = con.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    con.close()
    return render_template("news.html", news=news)

@app.route("/team")
def team():
    con = db()
    players = con.execute("SELECT id, name, role, goals, assists, saves, conceded, bio FROM players").fetchall()
    con.close()
    return render_template("team.html", players=players)

@app.route("/player/<int:id>")
def player(id):
    con = db()
    player = con.execute("SELECT id, name, role, goals, assists, saves, conceded, bio FROM players WHERE id=?", (id,)).fetchone()
    con.close()
    if not player:
        return "Игрок не найден", 404
    return render_template("player.html", player=player)

@app.route("/matches")
def matches():
    con = db()
    matches = con.execute("""
        SELECT m.id,
               t1.name as left_name, t1.logo_filename as left_logo,
               t2.name as right_name, t2.logo_filename as right_logo,
               m.score, m.date, m.result
        FROM matches m
        JOIN teams t1 ON m.team_left_id = t1.id
        JOIN teams t2 ON m.team_right_id = t2.id
        ORDER BY m.date DESC
    """).fetchall()
    con.close()
    return render_template("matches.html", matches=matches)

@app.route("/replays")
def replays():
    con = db()
    replays = con.execute("SELECT * FROM replays").fetchall()
    con.close()
    return render_template("replays.html", replays=replays)

# --- Аутентификация через 2FA ---
@app.route("/login", methods=["GET", "POST"])
def login():
    con = db()
    admins = con.execute("SELECT id, name, totp_secret FROM admins WHERE is_active=1").fetchall()
    con.close()

    if not admins:
        return redirect("/setup-first-admin")

    if request.method == "POST":
        code = request.form.get("code", "")
        if not code:
            return render_template("login.html", error="Введите код")

        for admin in admins:
            totp = pyotp.TOTP(admin[2])
            if totp.verify(code):
                session.permanent = True
                session["admin_id"] = admin[0]
                session["admin_name"] = admin[1]
                return redirect("/admin")

        return render_template("login.html", error="Неверный код")

    return render_template("login.html")

@app.route("/setup-first-admin", methods=["GET", "POST"])
def setup_first_admin():
    con = db()
    admins = con.execute("SELECT id FROM admins").fetchall()
    con.close()
    if admins:
        return redirect("/login")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "")
        secret = request.form.get("secret")

        if not name or not code or not secret:
            return render_template("setup_first_admin.html", error="Заполните все поля")

        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            con = db()
            con.execute("INSERT INTO admins (name, totp_secret) VALUES (?, ?)", (name, secret))
            con.commit()
            admin_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.close()
            session.permanent = True
            session["admin_id"] = admin_id
            session["admin_name"] = name
            return redirect("/admin")
        else:
            return render_template("setup_first_admin.html", secret=secret, error="Неверный код, попробуйте ещё раз")

    # GET: генерируем секрет
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name="site 123", issuer_name="site super good")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return render_template("setup_first_admin.html", secret=secret, qr=qr_base64)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --- Админка (защищённая) ---
@app.route("/admin")
def admin():
    if not session.get("admin_id"):
        return redirect("/login")

    con = db()
    players = con.execute("SELECT id, name, role, goals, assists, saves, conceded, bio FROM players").fetchall()
    teams = con.execute("SELECT * FROM teams ORDER BY name").fetchall()
    con.close()
    return render_template("admin.html", players=players, teams=teams, admin_name=session.get("admin_name"))

@app.route("/admin/news/add", methods=["POST"])
def add_news():
    if not session.get("admin_id"):
        return redirect("/login")
    title = request.form["title"]
    text = request.form["text"]
    preview = request.files.get("preview")
    preview_filename = None
    if preview and preview.filename != '' and allowed_file(preview.filename):
        filename = secure_filename(preview.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        safe_filename = f"news_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        preview.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_filename))
        preview_filename = safe_filename
    con = db()
    con.execute("INSERT INTO news (title, text, preview_filename) VALUES (?, ?, ?)",
                (title, text, preview_filename))
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/admin/player/add", methods=["POST"])
def add_player():
    if not session.get("admin_id"):
        return redirect("/login")
    name = request.form["name"]
    role = request.form["role"]
    bio = request.form.get("bio", "")
    if role == "goalie":
        goals = request.form.get("goalie_goals", 0)
        assists = 0
        saves = request.form.get("goalie_saves", 0)
        conceded = request.form.get("goalie_conceded", 0)
    else:
        goals = request.form.get("field_goals", 0)
        assists = request.form.get("field_assists", 0)
        saves = 0
        conceded = 0
    con = db()
    con.execute("""
        INSERT INTO players (name, role, goals, assists, saves, conceded, bio)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, role, goals, assists, saves, conceded, bio))
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/admin/match/add", methods=["POST"])
def add_match():
    if not session.get("admin_id"):
        return redirect("/login")
    team_left = request.form["team_left"]
    team_right = request.form["team_right"]
    score = request.form["score"]
    date = request.form["date"]
    result = request.form["result"]
    con = db()
    con.execute("""
        INSERT INTO matches(team_left_id, team_right_id, score, date, result)
        VALUES (?,?,?,?,?)
    """, (team_left, team_right, score, date, result))
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/admin/replay/add", methods=["POST"])
def add_replay():
    if not session.get("admin_id"):
        return redirect("/login")
    title = request.form["title"]
    file = request.files.get("replay_file")
    filename = None
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    con = db()
    con.execute("INSERT INTO replays(title, filename) VALUES(?,?)", (title, filename))
    con.commit()
    con.close()
    return redirect("/admin")

# --- Редактирование игрока ---
@app.route("/edit_player/<int:id>", methods=["GET", "POST"])
def edit_player(id):
    if not session.get("admin_id"):
        return redirect("/login")

    con = db()
    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        bio = request.form.get("bio", "")
        if role == "goalie":
            goals = request.form.get("goalie_goals", 0)
            assists = 0
            saves = request.form.get("goalie_saves", 0)
            conceded = request.form.get("goalie_conceded", 0)
        else:
            goals = request.form.get("field_goals", 0)
            assists = request.form.get("field_assists", 0)
            saves = 0
            conceded = 0
        con.execute("""
            UPDATE players
            SET name=?, role=?, goals=?, assists=?, saves=?, conceded=?, bio=?
            WHERE id=?
        """, (name, role, goals, assists, saves, conceded, bio, id))
        con.commit()
        con.close()
        return redirect("/admin")
    else:
        player = con.execute("SELECT * FROM players WHERE id=?", (id,)).fetchone()
        con.close()
        if not player:
            return "Игрок не найден", 404
        return render_template("edit_player.html", player=player)

# --- Управление администраторами ---
@app.route("/admin/admins")
def list_admins():
    if not session.get("admin_id"):
        return redirect("/login")
    con = db()
    admins = con.execute("SELECT id, name, is_active FROM admins").fetchall()
    con.close()
    return render_template("admin_admins.html", admins=admins)

@app.route("/admin/admins/add", methods=["GET", "POST"])
def add_admin():
    if not session.get("admin_id"):
        return redirect("/login")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "")
        secret = request.form.get("secret")

        if not name or not code or not secret:
            return render_template("add_admin.html", error="Заполните все поля")

        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            con = db()
            con.execute("INSERT INTO admins (name, totp_secret) VALUES (?, ?)", (name, secret))
            con.commit()
            con.close()
            return redirect("/admin/admins")
        else:
            return render_template("add_admin.html", secret=secret, error="Неверный код, попробуйте ещё раз")

    # GET: генерируем секрет
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name="Minecraft Hockey Admin", issuer_name="Minecraft Hockey")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return render_template("add_admin.html", secret=secret, qr=qr_base64)

@app.route("/admin/admins/toggle/<int:id>")
def toggle_admin(id):
    if not session.get("admin_id"):
        return redirect("/login")
    if id == session["admin_id"]:
        flash("Нельзя деактивировать самого себя")
        return redirect("/admin/admins")
    con = db()
    admin = con.execute("SELECT is_active FROM admins WHERE id=?", (id,)).fetchone()
    if admin:
        new_status = 0 if admin[0] else 1
        con.execute("UPDATE admins SET is_active=? WHERE id=?", (new_status, id))
        con.commit()
    con.close()
    return redirect("/admin/admins")

@app.route("/about")
def about():
    con = db()
    return render_template("about.html")

@app.route("/admin/admins/delete/<int:id>")
def delete_admin(id):
    if not session.get("admin_id"):
        return redirect("/login")
    if id == session["admin_id"]:
        flash("Нельзя удалить самого себя")
        return redirect("/admin/admins")
    con = db()
    con.execute("DELETE FROM admins WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect("/admin/admins")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)