import os
import uuid
import json
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app, jsonify
)
from werkzeug.utils import secure_filename
from config import Config
from database.db import query_db, execute_db
from routes.auth import login_required, role_required
from agents.garbage_detection import analyze_garbage_image
from agents.complaint_priority import calculate_priority_score

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@citizen_bp.route("/")
@citizen_bp.route("/dashboard")
@login_required
@role_required(["citizen", "admin"])
def dashboard():
    user_id = session["user_id"]
    
    # Query summary counts for citizen
    total_count = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ?", [user_id], one=True)["cnt"]
    pending_count = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status = 'Pending'", [user_id], one=True)["cnt"]
    active_count = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status IN ('Assigned', 'In Progress')", [user_id], one=True)["cnt"]
    resolved_count = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE user_id = ? AND status = 'Resolved'", [user_id], one=True)["cnt"]
    
    # Recent complaints
    recent_complaints = query_db("""
        SELECT c.*, 
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
        FROM complaints c
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC
        LIMIT 6
    """, [user_id])
    
    # Parse detected items JSON for template rendering
    complaints_list = []
    for comp in recent_complaints:
        c_dict = dict(comp)
        try:
            c_dict["detected_items_list"] = json.loads(c_dict["ai_detected_items"] or "[]")
        except Exception:
            c_dict["detected_items_list"] = []
        complaints_list.append(c_dict)

    stats = {
        "total": total_count,
        "pending": pending_count,
        "active": active_count,
        "resolved": resolved_count
    }

    return render_template(
        "citizen_dashboard.html",
        stats=stats,
        complaints=complaints_list,
        default_lat=Config.DEFAULT_LAT,
        default_lng=Config.DEFAULT_LNG
    )

@citizen_bp.route("/report", methods=["GET", "POST"])
@login_required
@role_required(["citizen", "admin"])
def report_garbage():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        address = request.form.get("address", "").strip()
        landmark = request.form.get("landmark", "").strip()
        lat_str = request.form.get("latitude", "").strip()
        lng_str = request.form.get("longitude", "").strip()
        
        # File validation
        if "garbage_photo" not in request.files:
            flash("Please upload a photograph of the garbage.", "danger")
            return redirect(request.url)
            
        file = request.files["garbage_photo"]
        if file.filename == "":
            flash("No file was selected for upload.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Allowed image formats: JPG, PNG, WEBP, JPEG.", "danger")
            return redirect(request.url)

        if not title or not description:
            flash("Please provide a brief title and description of the garbage issue.", "danger")
            return redirect(request.url)

        try:
            latitude = float(lat_str) if lat_str else Config.DEFAULT_LAT
            longitude = float(lng_str) if lng_str else Config.DEFAULT_LNG
        except ValueError:
            latitude = Config.DEFAULT_LAT
            longitude = Config.DEFAULT_LNG

        # Save uploaded image with secure unique name
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"garbage_{uuid.uuid4().hex[:12]}.{ext}"
        save_path = Config.UPLOAD_FOLDER / unique_filename
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        file.save(save_path)
        
        relative_img_path = f"complaints/{unique_filename}"

        # Run AI Garbage Detection Agent
        ai_res = analyze_garbage_image(save_path)
        
        waste_type = ai_res.get("waste_type", "Mixed waste")
        severity = ai_res.get("severity", "Medium")
        confidence = ai_res.get("confidence", 0.85)
        explanation = ai_res.get("explanation", "")
        recommendation = ai_res.get("recommendation", "")
        detected_items_json = json.dumps(ai_res.get("detected_items", []))

        # Insert complaint
        user_id = session["user_id"]
        complaint_id = execute_db("""
            INSERT INTO complaints (
                user_id, title, description, waste_type, severity, status,
                address, landmark, latitude, longitude,
                ai_waste_type, ai_severity, ai_confidence,
                ai_explanation, ai_recommendation, ai_detected_items
            ) VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, description, waste_type, severity,
            address, landmark, latitude, longitude,
            waste_type, severity, confidence,
            explanation, recommendation, detected_items_json
        ))

        # Insert image record
        execute_db("""
            INSERT INTO complaint_images (complaint_id, image_type, file_path, caption)
            VALUES (?, 'before', ?, ?)
        """, (complaint_id, relative_img_path, "Citizen uploaded before photo"))

        # Log status history
        execute_db("""
            INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes)
            VALUES (?, ?, NULL, 'Pending', 'Complaint filed by citizen. AI automated classification applied.')
        """, (complaint_id, user_id))

        flash(
            f"Complaint #{complaint_id} submitted! AI classified this as '{waste_type}' with {severity} severity.",
            "success"
        )
        return redirect(url_for("citizen.complaint_detail", complaint_id=complaint_id))

    return render_template(
        "report_garbage.html",
        default_lat=Config.DEFAULT_LAT,
        default_lng=Config.DEFAULT_LNG
    )

@citizen_bp.route("/complaints")
@login_required
@role_required(["citizen", "admin"])
def complaints_list():
    user_id = session["user_id"]
    status_filter = request.args.get("status", "all")
    
    if status_filter != "all":
        rows = query_db("""
            SELECT c.*, 
                   (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
                   (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
            FROM complaints c
            WHERE c.user_id = ? AND c.status = ?
            ORDER BY c.created_at DESC
        """, [user_id, status_filter])
    else:
        rows = query_db("""
            SELECT c.*, 
                   (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
                   (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
            FROM complaints c
            WHERE c.user_id = ?
            ORDER BY c.created_at DESC
        """, [user_id])

    complaints = []
    for r in rows:
        c_dict = dict(r)
        try:
            c_dict["detected_items_list"] = json.loads(c_dict["ai_detected_items"] or "[]")
        except Exception:
            c_dict["detected_items_list"] = []
        complaints.append(c_dict)

    return render_template("complaints.html", complaints=complaints, active_filter=status_filter)

@citizen_bp.route("/complaint/<int:complaint_id>")
@login_required
def complaint_detail(complaint_id):
    user_id = session["user_id"]
    user_role = session.get("user_role")

    # If citizen, verify ownership
    if user_role == "citizen":
        complaint = query_db("SELECT * FROM complaints WHERE id = ? AND user_id = ?", [complaint_id, user_id], one=True)
    else:
        complaint = query_db("SELECT * FROM complaints WHERE id = ?", [complaint_id], one=True)

    if not complaint:
        flash("Complaint not found or access restricted.", "danger")
        return redirect(url_for("citizen.dashboard"))

    c_dict = dict(complaint)
    try:
        c_dict["detected_items_list"] = json.loads(c_dict["ai_detected_items"] or "[]")
    except Exception:
        c_dict["detected_items_list"] = []

    # Get images
    images = query_db("SELECT * FROM complaint_images WHERE complaint_id = ? ORDER BY uploaded_at ASC", [complaint_id])
    
    # Get status timeline history
    timeline = query_db("""
        SELECT sh.*, u.name as actor_name, u.role as actor_role
        FROM status_history sh
        LEFT JOIN users u ON sh.changed_by = u.id
        WHERE sh.complaint_id = ?
        ORDER BY sh.created_at ASC
    """, [complaint_id])

    # Get assignment details if any
    assignment = query_db("""
        SELECT a.*, w.full_name as worker_name, w.phone as worker_phone, w.zone as worker_zone
        FROM assignments a
        JOIN workers w ON a.worker_id = w.id
        WHERE a.complaint_id = ?
        ORDER BY a.assigned_at DESC
        LIMIT 1
    """, [complaint_id], one=True)

    # Compute priority badge
    priority_info = calculate_priority_score(c_dict)

    return render_template(
        "complaint_detail.html",
        complaint=c_dict,
        images=images,
        timeline=timeline,
        assignment=assignment,
        priority=priority_info
    )
