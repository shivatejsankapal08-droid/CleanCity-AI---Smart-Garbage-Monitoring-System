import os
from flask import Flask, render_template, redirect, url_for, session, send_from_directory, request, jsonify
from config import Config
from database.db import close_db, init_db, seed_data, query_db
from routes.auth import auth_bp
from routes.citizen import citizen_bp
from routes.worker import worker_bp
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directories exist
    Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.PROOFS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Database teardown
    app.teardown_appcontext(close_db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(admin_bp)

    # Jinja Custom Filters
    @app.template_filter("dt_format")
    def dt_format_filter(value, length=16):
        if not value:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M") if length > 10 else value.strftime("%Y-%m-%d")
        return str(value)[:length]

    # Global context processor
    @app.context_processor
    def inject_global_data():
        user = None
        if "user_id" in session:
            user = {
                "id": session.get("user_id"),
                "name": session.get("user_name"),
                "email": session.get("user_email"),
                "role": session.get("user_role")
            }
        return {
            "current_user": user,
            "app_name": "CleanCity AI",
            "gemini_enabled": bool(Config.GEMINI_API_KEY)
        }

    # Public Landing Page
    @app.route("/")
    def index():
        if "user_id" in session:
            role = session.get("user_role")
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif role == "worker":
                return redirect(url_for("worker.dashboard"))
            else:
                return redirect(url_for("citizen.dashboard"))

        # Public stats for landing page hero
        total_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints", one=True)["cnt"]
        resolved_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Resolved'", one=True)["cnt"]
        active_workers = query_db("SELECT COUNT(*) as cnt FROM workers WHERE status != 'Off-Duty'", one=True)["cnt"]
        
        rate = round((resolved_complaints / total_complaints * 100), 1) if total_complaints > 0 else 92.5

        return render_template(
            "landing.html",
            stats={
                "total": total_complaints,
                "resolved": resolved_complaints,
                "rate": rate,
                "workers": active_workers
            }
        )

    # Public City Garbage Map View
    @app.route("/map")
    def public_map():
        return render_template(
            "map.html",
            default_lat=Config.DEFAULT_LAT,
            default_lng=Config.DEFAULT_LNG,
            is_public=True
        )

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template("404.html", message="Uploaded file exceeds 16MB limit."), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("404.html", message="An internal server error occurred."), 500

    # Initialize and seed database upon startup
    with app.app_context():
        init_db()
        seed_data()

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  CleanCity AI - Smart Garbage Monitoring System")
    print(f"  Server running at: http://127.0.0.1:{port}")
    print(f"  Gemini Vision AI: {'Active (API Key loaded)' if Config.GEMINI_API_KEY else 'Fallback Mode (Autonomous Heuristic)'}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=True)
