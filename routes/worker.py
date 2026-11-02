import os
import uuid
import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app
)
from werkzeug.utils import secure_filename
from config import Config
from database.db import query_db, execute_db
from routes.auth import login_required, role_required

worker_bp = Blueprint("worker", __name__, url_prefix="/worker")

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@worker_bp.route("/")
@worker_bp.route("/dashboard")
@login_required
@role_required(["worker", "admin"])
def dashboard():
    user_id = session["user_id"]
    
    # Get worker record
    worker = query_db("SELECT * FROM workers WHERE user_id = ?", [user_id], one=True)
    if not worker and session.get("user_role") == "admin":
        # Fallback for admin visiting worker dashboard
        worker = query_db("SELECT * FROM workers LIMIT 1", one=True)
        
    if not worker:
        flash("Worker profile not found.", "warning")
        return redirect(url_for("auth.login"))

    worker_id = worker["id"]

    # Counts
    assigned_count = query_db("""
        SELECT COUNT(*) as cnt FROM assignments a
        JOIN complaints c ON a.complaint_id = c.id
        WHERE a.worker_id = ? AND a.status = 'Assigned' AND c.status = 'Assigned'
    """, [worker_id], one=True)["cnt"]

    in_progress_count = query_db("""
        SELECT COUNT(*) as cnt FROM assignments a
        JOIN complaints c ON a.complaint_id = c.id
        WHERE a.worker_id = ? AND c.status = 'In Progress'
    """, [worker_id], one=True)["cnt"]

    completed_count = query_db("""
        SELECT COUNT(*) as cnt FROM assignments 
        WHERE worker_id = ? AND status = 'Completed'
    """, [worker_id], one=True)["cnt"]

    # Active tasks (Assigned or In Progress)
    tasks_query = query_db("""
        SELECT c.*, a.id as assignment_id, a.assigned_at, a.notes as assignment_notes,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
               u.name as citizen_name, u.phone as citizen_phone
        FROM assignments a
        JOIN complaints c ON a.complaint_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE a.worker_id = ? AND c.status IN ('Assigned', 'In Progress')
        ORDER BY 
            CASE c.severity 
                WHEN 'Critical' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                ELSE 4 
            END ASC,
            c.created_at ASC
    """, [worker_id])

    active_tasks = []
    for t in tasks_query:
        t_dict = dict(t)
        try:
            t_dict["detected_items_list"] = json.loads(t_dict["ai_detected_items"] or "[]")
        except Exception:
            t_dict["detected_items_list"] = []
        active_tasks.append(t_dict)

    # Completed tasks history (last 5)
    completed_history = query_db("""
        SELECT c.*, a.completed_at,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
        FROM assignments a
        JOIN complaints c ON a.complaint_id = c.id
        WHERE a.worker_id = ? AND c.status = 'Resolved'
        ORDER BY a.completed_at DESC
        LIMIT 5
    """, [worker_id])

    return render_template(
        "worker_dashboard.html",
        worker=worker,
        stats={
            "assigned": assigned_count,
            "in_progress": in_progress_count,
            "completed": completed_count
        },
        active_tasks=active_tasks,
        completed_history=completed_history
    )

@worker_bp.route("/task/<int:complaint_id>/start", methods=["POST"])
@login_required
@role_required(["worker", "admin"])
def start_task(complaint_id):
    user_id = session["user_id"]
    
    # Update complaint status to In Progress
    execute_db("""
        UPDATE complaints SET status = 'In Progress', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, [complaint_id])
    
    # Update assignment
    execute_db("""
        UPDATE assignments SET status = 'In Progress'
        WHERE complaint_id = ?
    """, [complaint_id])

    # Record status history
    execute_db("""
        INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes)
        VALUES (?, ?, 'Assigned', 'In Progress', 'Sanitation worker dispatched and commenced cleaning on-site.')
    """, (complaint_id, user_id))

    flash(f"Task #{complaint_id} marked as In Progress. Safe travels!", "info")
    return redirect(url_for("worker.dashboard"))

@worker_bp.route("/task/<int:complaint_id>/complete", methods=["POST"])
@login_required
@role_required(["worker", "admin"])
def complete_task(complaint_id):
    user_id = session["user_id"]
    notes = request.form.get("completion_notes", "Sanitation and waste clearance completed successfully.").strip()
    
    # Handle proof after-photo upload
    after_img_rel_path = None
    if "after_photo" in request.files:
        file = request.files["after_photo"]
        if file and file.filename != "" and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            unique_filename = f"proof_{complaint_id}_{uuid.uuid4().hex[:8]}.{ext}"
            save_path = Config.PROOFS_FOLDER / unique_filename
            Config.PROOFS_FOLDER.mkdir(parents=True, exist_ok=True)
            file.save(save_path)
            after_img_rel_path = f"proofs/{unique_filename}"
            
            # Record after image
            execute_db("""
                INSERT INTO complaint_images (complaint_id, image_type, file_path, caption)
                VALUES (?, 'after', ?, ?)
            """, (complaint_id, after_img_rel_path, "Worker post-cleanup verification photograph"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update complaint status to Resolved
    execute_db("""
        UPDATE complaints SET status = 'Resolved', updated_at = ?
        WHERE id = ?
    """, (now_str, complaint_id))

    # Update assignment status
    execute_db("""
        UPDATE assignments SET status = 'Completed', completed_at = ?, notes = ?
        WHERE complaint_id = ?
    """, (now_str, notes, complaint_id))

    # Record status history
    execute_db("""
        INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes)
        VALUES (?, ?, 'In Progress', 'Resolved', ?)
    """, (complaint_id, user_id, f"Resolved by worker. Notes: {notes}"))

    flash(f"Excellent work! Task #{complaint_id} marked as Resolved.", "success")
    return redirect(url_for("worker.dashboard"))
