import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from database.db import query_db, execute_db
from routes.auth import login_required, role_required
from config import Config
from agents.complaint_priority import calculate_priority_score, find_hotspots

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@role_required(["admin"])
def dashboard():
    # Key statistics
    total_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints", one=True)["cnt"]
    pending_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Pending'", one=True)["cnt"]
    assigned_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Assigned'", one=True)["cnt"]
    inprogress_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'In Progress'", one=True)["cnt"]
    resolved_complaints = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Resolved'", one=True)["cnt"]
    active_workers = query_db("SELECT COUNT(*) as cnt FROM workers WHERE status != 'Off-Duty'", one=True)["cnt"]

    # Resolution rate calculation
    resolution_rate = round((resolved_complaints / total_complaints * 100), 1) if total_complaints > 0 else 0

    # Hotspots summary
    hotspots = find_hotspots(threshold_meters=350, min_complaints=2)

    # Active complaints list with worker assignment info
    complaints_raw = query_db("""
        SELECT c.*, 
               u.name as citizen_name, u.phone as citizen_phone,
               w.full_name as assigned_worker_name, w.id as assigned_worker_id,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN assignments a ON c.id = a.complaint_id AND a.status != 'Cancelled'
        LEFT JOIN workers w ON a.worker_id = w.id
        ORDER BY 
            CASE c.status 
                WHEN 'Pending' THEN 1 
                WHEN 'Assigned' THEN 2 
                WHEN 'In Progress' THEN 3 
                ELSE 4 
            END,
            CASE c.severity
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                ELSE 4
            END,
            c.created_at DESC
    """)

    complaints = []
    for c in complaints_raw:
        c_dict = dict(c)
        try:
            c_dict["detected_items_list"] = json.loads(c_dict["ai_detected_items"] or "[]")
        except Exception:
            c_dict["detected_items_list"] = []
        c_dict["priority_info"] = calculate_priority_score(c_dict)
        complaints.append(c_dict)

    # Available workers for assignment modal
    workers = query_db("""
        SELECT w.*, 
               (SELECT COUNT(*) FROM assignments a 
                JOIN complaints c ON a.complaint_id = c.id 
                WHERE a.worker_id = w.id AND c.status IN ('Assigned', 'In Progress')) as active_tasks
        FROM workers w
        ORDER BY active_tasks ASC, w.full_name ASC
    """)

    stats = {
        "total": total_complaints,
        "pending": pending_complaints,
        "assigned": assigned_complaints,
        "in_progress": inprogress_complaints,
        "resolved": resolved_complaints,
        "resolution_rate": resolution_rate,
        "active_workers": active_workers,
        "hotspots_count": len(hotspots)
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        complaints=complaints,
        workers=workers,
        hotspots=hotspots,
        default_lat=Config.DEFAULT_LAT,
        default_lng=Config.DEFAULT_LNG
    )

@admin_bp.route("/assign", methods=["POST"])
@login_required
@role_required(["admin"])
def assign_worker():
    complaint_id = request.form.get("complaint_id")
    worker_id = request.form.get("worker_id")
    notes = request.form.get("assignment_notes", "").strip()
    admin_id = session["user_id"]

    if not complaint_id or not worker_id:
        flash("Invalid assignment request.", "danger")
        return redirect(url_for("admin.dashboard"))

    worker = query_db("SELECT full_name FROM workers WHERE id = ?", [worker_id], one=True)
    worker_name = worker["full_name"] if worker else f"Worker #{worker_id}"

    # Check if assignment already exists
    existing = query_db("SELECT id FROM assignments WHERE complaint_id = ?", [complaint_id], one=True)
    if existing:
        execute_db("""
            UPDATE assignments 
            SET worker_id = ?, assigned_by = ?, assigned_at = CURRENT_TIMESTAMP, status = 'Assigned', notes = ?
            WHERE complaint_id = ?
        """, (worker_id, admin_id, notes, complaint_id))
    else:
        execute_db("""
            INSERT INTO assignments (complaint_id, worker_id, assigned_by, notes, status)
            VALUES (?, ?, ?, ?, 'Assigned')
        """, (complaint_id, worker_id, admin_id, notes))

    # Update complaint status to Assigned
    execute_db("""
        UPDATE complaints SET status = 'Assigned', updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, [complaint_id])

    # Record in status history
    execute_db("""
        INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes)
        VALUES (?, ?, 'Pending', 'Assigned', ?)
    """, (complaint_id, admin_id, f"Assigned to {worker_name}. {notes}"))

    flash(f"Complaint #{complaint_id} assigned successfully to {worker_name}.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))

@admin_bp.route("/status/update", methods=["POST"])
@login_required
@role_required(["admin"])
def update_status():
    complaint_id = request.form.get("complaint_id")
    new_status = request.form.get("status")
    notes = request.form.get("notes", "").strip()
    admin_id = session["user_id"]

    if new_status not in Config.STATUS_LIST:
        flash("Invalid status specified.", "danger")
        return redirect(url_for("admin.dashboard"))

    current = query_db("SELECT status FROM complaints WHERE id = ?", [complaint_id], one=True)
    old_status = current["status"] if current else "Unknown"

    execute_db("""
        UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (new_status, complaint_id))

    execute_db("""
        INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (complaint_id, admin_id, old_status, new_status, notes or f"Status updated by Administrator."))

    flash(f"Complaint #{complaint_id} status updated to '{new_status}'.", "info")
    return redirect(request.referrer or url_for("admin.dashboard"))

@admin_bp.route("/map")
@login_required
@role_required(["admin"])
def map_view():
    hotspots = find_hotspots(threshold_meters=350, min_complaints=2)
    return render_template(
        "map.html",
        hotspots=hotspots,
        default_lat=Config.DEFAULT_LAT,
        default_lng=Config.DEFAULT_LNG
    )

@admin_bp.route("/analytics")
@login_required
@role_required(["admin"])
def analytics_view():
    hotspots = find_hotspots(threshold_meters=350, min_complaints=2)
    
    # Waste Category Breakdown
    waste_dist = query_db("""
        SELECT waste_type, COUNT(*) as count 
        FROM complaints 
        GROUP BY waste_type 
        ORDER BY count DESC
    """)
    
    # Severity Distribution
    severity_dist = query_db("""
        SELECT severity, COUNT(*) as count 
        FROM complaints 
        GROUP BY severity
    """)

    # Status Distribution
    status_dist = query_db("""
        SELECT status, COUNT(*) as count 
        FROM complaints 
        GROUP BY status
    """)

    # Total & Resolution metrics
    total = query_db("SELECT COUNT(*) as cnt FROM complaints", one=True)["cnt"]
    resolved = query_db("SELECT COUNT(*) as cnt FROM complaints WHERE status = 'Resolved'", one=True)["cnt"]
    rate = round((resolved / total * 100), 1) if total > 0 else 0

    return render_template(
        "analytics.html",
        hotspots=hotspots,
        total_complaints=total,
        resolved_complaints=resolved,
        resolution_rate=rate,
        waste_dist=waste_dist,
        severity_dist=severity_dist,
        status_dist=status_dist
    )

# Workers Management in Admin
@admin_bp.route("/workers")
@login_required
@role_required(["admin"])
def workers_list():
    workers = query_db("""
        SELECT w.*, u.email,
               (SELECT COUNT(*) FROM assignments a JOIN complaints c ON a.complaint_id = c.id WHERE a.worker_id = w.id AND c.status = 'Assigned') as pending_tasks,
               (SELECT COUNT(*) FROM assignments a JOIN complaints c ON a.complaint_id = c.id WHERE a.worker_id = w.id AND c.status = 'In Progress') as in_progress_tasks,
               (SELECT COUNT(*) FROM assignments a WHERE a.worker_id = w.id AND a.status = 'Completed') as completed_tasks
        FROM workers w
        JOIN users u ON w.user_id = u.id
        ORDER BY w.full_name ASC
    """)
    return render_template("workers.html", workers=workers)

@admin_bp.route("/workers/toggle-status/<int:worker_id>", methods=["POST"])
@login_required
@role_required(["admin"])
def toggle_worker_status(worker_id):
    current = query_db("SELECT status FROM workers WHERE id = ?", [worker_id], one=True)
    if current:
        new_status = "Available" if current["status"] != "Available" else "Busy"
        execute_db("UPDATE workers SET status = ? WHERE id = ?", [new_status, worker_id])
        flash(f"Worker status updated to '{new_status}'.", "info")
    return redirect(url_for("admin.workers_list"))

# JSON APIs for Leaflet & Chart.js
@admin_bp.route("/api/map-data")
def api_map_data():
    """Returns GeoJSON-ready markers and hotspot clusters."""
    complaints = query_db("""
        SELECT c.id, c.title, c.description, c.waste_type, c.severity, c.status,
               c.address, c.landmark, c.latitude, c.longitude, c.ai_confidence, c.created_at,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'before' LIMIT 1) as before_image,
               (SELECT file_path FROM complaint_images WHERE complaint_id = c.id AND image_type = 'after' LIMIT 1) as after_image
        FROM complaints c
        WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
    """)

    markers = []
    for c in complaints:
        markers.append({
            "id": c["id"],
            "title": c["title"],
            "description": c["description"],
            "waste_type": c["waste_type"],
            "severity": c["severity"],
            "status": c["status"],
            "address": c["address"] or "No address specified",
            "lat": c["latitude"],
            "lng": c["longitude"],
            "image": c["before_image"] or "",
            "after_image": c["after_image"] or "",
            "date": str(c["created_at"])[:10]
        })

    hotspots = find_hotspots(threshold_meters=350, min_complaints=2)

    return jsonify({
        "status": "success",
        "markers": markers,
        "hotspots": hotspots
    })

@admin_bp.route("/api/analytics-data")
def api_analytics_data():
    """Returns analytics data formatted for Chart.js."""
    # Waste Category Distribution
    waste_rows = query_db("""
        SELECT waste_type, COUNT(*) as cnt 
        FROM complaints 
        GROUP BY waste_type
    """)
    waste_labels = [r["waste_type"] for r in waste_rows]
    waste_counts = [r["cnt"] for r in waste_rows]

    # Severity Distribution
    sev_rows = query_db("""
        SELECT severity, COUNT(*) as cnt 
        FROM complaints 
        GROUP BY severity
    """)
    sev_map = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in sev_rows:
        if r["severity"] in sev_map:
            sev_map[r["severity"]] = r["cnt"]

    # Status Breakdown
    status_rows = query_db("""
        SELECT status, COUNT(*) as cnt 
        FROM complaints 
        GROUP BY status
    """)
    status_labels = [r["status"] for r in status_rows]
    status_counts = [r["cnt"] for r in status_rows]

    # Monthly Trends (e.g. past 6 months)
    monthly_rows = query_db("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as cnt
        FROM complaints
        GROUP BY month
        ORDER BY month ASC
        LIMIT 6
    """)
    month_labels = [r["month"] for r in monthly_rows]
    month_counts = [r["cnt"] for r in monthly_rows]

    return jsonify({
        "waste": {
            "labels": waste_labels,
            "counts": waste_counts
        },
        "severity": {
            "labels": list(sev_map.keys()),
            "counts": list(sev_map.values())
        },
        "status": {
            "labels": status_labels,
            "counts": status_counts
        },
        "monthly": {
            "labels": month_labels,
            "counts": month_counts
        }
    })
