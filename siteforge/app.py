import os
import sqlite3
import json
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, abort, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SITEFORGE_SECRET_KEY", "dev-secret-change-this")
DB_PATH = "siteforge.db"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGES_PER_SECTION = 5

SECTION_KEYS = ["about", "services", "gallery", "testimonials", "contact"]

COLOR_THEMES = {
    "indigo": {"primary": "#4f46e5", "light": "#e0e7ff", "dark": "#312e81"},
    "emerald": {"primary": "#059669", "light": "#d1fae5", "dark": "#064e3b"},
    "rose": {"primary": "#e11d48", "light": "#ffe4e6", "dark": "#881337"},
    "amber": {"primary": "#d97706", "light": "#fef3c7", "dark": "#78350f"},
    "slate": {"primary": "#475569", "light": "#e2e8f0", "dark": "#1e293b"},
    "violet": {"primary": "#7c3aed", "light": "#ede9fe", "dark": "#4c1d95"},
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sites (
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            site_name TEXT NOT NULL,
            category TEXT,
            color_theme TEXT,
            sections TEXT NOT NULL,
            images TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_section_images(site_id, files):
    """Save up to MAX_IMAGES_PER_SECTION uploaded images per section.
    Returns {section_key: [relative_path, ...]}"""
    images = {}
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    for key in SECTION_KEYS:
        uploaded = files.getlist(f"images_{key}")
        saved_paths = []
        for i, file in enumerate(uploaded[:MAX_IMAGES_PER_SECTION]):
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                unique = uuid.uuid4().hex[:6]
                filename = secure_filename(f"{site_id}_{key}_{i}_{unique}.{ext}")
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                saved_paths.append(f"uploads/{filename}")
        if saved_paths:
            images[key] = saved_paths
    return images


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


# ---------- Auth ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not password:
            error = "Name and password are required."
        elif password != confirm:
            error = "Passwords don't match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            conn = get_db()
            existing = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
            if existing:
                error = "That name is already taken."
            else:
                user_id = uuid.uuid4().hex[:8]
                conn.execute(
                    "INSERT INTO users (id, name, password_hash) VALUES (?, ?, ?)",
                    (user_id, name, generate_password_hash(password)),
                )
                conn.commit()
                session["user_id"] = user_id
                session["user_name"] = name
                conn.close()
                return redirect(url_for("home"))
            conn.close()

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            next_path = request.args.get("next") or url_for("home")
            return redirect(next_path)
        error = "Wrong name or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Core app ----------

@app.route("/")
@login_required
def home():
    conn = get_db()
    recent = conn.execute(
        "SELECT id, site_name, category, color_theme, created_at FROM sites "
        "WHERE owner_id = ? ORDER BY created_at DESC LIMIT 6",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template(
        "form.html",
        section_keys=SECTION_KEYS,
        themes=COLOR_THEMES,
        recent_sites=recent,
        user_name=session.get("user_name"),
        max_images=MAX_IMAGES_PER_SECTION,
    )


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    site_name = request.form.get("site_name", "").strip() or "My Website"
    category = request.form.get("category", "").strip() or "General"
    color_theme = request.form.get("color_theme", "indigo")
    if color_theme not in COLOR_THEMES:
        color_theme = "indigo"

    selected_sections = request.form.getlist("sections")
    sections = {}
    for key in selected_sections:
        if key in SECTION_KEYS:
            content = request.form.get(f"content_{key}", "").strip()
            if content:
                sections[key] = content

    if not sections:
        return redirect(url_for("home"))

    site_id = uuid.uuid4().hex[:8]
    images = save_section_images(site_id, request.files)

    conn = get_db()
    conn.execute(
        "INSERT INTO sites (id, owner_id, site_name, category, color_theme, sections, images) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (site_id, session["user_id"], site_name, category, color_theme, json.dumps(sections), json.dumps(images)),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("preview", site_id=site_id))


@app.route("/preview/<site_id>")
def preview(site_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    conn.close()

    if row is None:
        abort(404)

    sections = json.loads(row["sections"])
    images = json.loads(row["images"]) if row["images"] else {}
    theme = COLOR_THEMES.get(row["color_theme"], COLOR_THEMES["indigo"])
    is_owner = session.get("user_id") == row["owner_id"]

    return render_template(
        "site_template.html",
        site_id=site_id,
        site_name=row["site_name"],
        category=row["category"],
        sections=sections,
        images=images,
        theme=theme,
        section_order=SECTION_KEYS,
        is_owner=is_owner,
    )


@app.route("/edit/<site_id>", methods=["GET", "POST"])
@login_required
def edit(site_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()

    if row is None:
        conn.close()
        abort(404)

    if row["owner_id"] != session["user_id"]:
        conn.close()
        abort(403)

    if request.method == "POST":
        site_name = request.form.get("site_name", "").strip() or row["site_name"]
        category = request.form.get("category", "").strip() or row["category"]
        color_theme = request.form.get("color_theme", row["color_theme"])
        if color_theme not in COLOR_THEMES:
            color_theme = row["color_theme"]

        selected_sections = request.form.getlist("sections")
        sections = {}
        for key in selected_sections:
            if key in SECTION_KEYS:
                content = request.form.get(f"content_{key}", "").strip()
                if content:
                    sections[key] = content

        images = json.loads(row["images"]) if row["images"] else {}
        new_images = save_section_images(site_id, request.files)
        images.update(new_images)

        conn.execute(
            "UPDATE sites SET site_name=?, category=?, color_theme=?, sections=?, images=? WHERE id=?",
            (site_name, category, color_theme, json.dumps(sections), json.dumps(images), site_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("preview", site_id=site_id))

    sections = json.loads(row["sections"])
    images = json.loads(row["images"]) if row["images"] else {}
    conn.close()
    return render_template(
        "edit.html",
        site_id=site_id,
        site_name=row["site_name"],
        category=row["category"],
        color_theme=row["color_theme"],
        sections=sections,
        images=images,
        section_keys=SECTION_KEYS,
        themes=COLOR_THEMES,
        max_images=MAX_IMAGES_PER_SECTION,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
