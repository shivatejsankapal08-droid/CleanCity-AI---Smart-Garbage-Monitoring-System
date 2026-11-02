from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db, execute_db

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in first.", "warning")
                return redirect(url_for("auth.login", next=request.url))
            user_role = session.get("user_role")
            if user_role not in allowed_roles:
                flash(f"Access restricted. Required role: {', '.join(allowed_roles)}.", "danger")
                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user_role == "worker":
                    return redirect(url_for("worker.dashboard"))
                else:
                    return redirect(url_for("citizen.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        role = session.get("user_role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "worker":
            return redirect(url_for("worker.dashboard"))
        return redirect(url_for("citizen.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        user = query_db("SELECT * FROM users WHERE email = ?", [email], one=True)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html")

        # Set session
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        flash(f"Welcome back, {user['name']}! Signed in as {user['role'].capitalize()}.", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        if user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        elif user["role"] == "worker":
            return redirect(url_for("worker.dashboard"))
        else:
            return redirect(url_for("citizen.dashboard"))

    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("citizen.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "citizen").strip().lower()

        # Enforce valid roles: citizen, worker (admin cannot be self-registered publicly)
        if role not in ["citizen", "worker"]:
            role = "citizen"

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        existing = query_db("SELECT id FROM users WHERE email = ?", [email], one=True)
        if existing:
            flash("An account with that email already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        pw_hash = generate_password_hash(password)
        user_id = execute_db("""
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, pw_hash, role, phone, address))

        # If registered as worker, create worker entry
        if role == "worker":
            zone = request.form.get("zone", "General Sanitation Zone")
            vehicle = request.form.get("vehicle_type", "Garbage Truck")
            execute_db("""
                INSERT INTO workers (user_id, full_name, phone, zone, status, vehicle_type)
                VALUES (?, ?, ?, ?, 'Available', ?)
            """, (user_id, name, phone, zone, vehicle))

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))
