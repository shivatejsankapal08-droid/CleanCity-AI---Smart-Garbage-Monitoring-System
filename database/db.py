import sqlite3
import json
from datetime import datetime, timedelta
from flask import g, current_app
from werkzeug.security import generate_password_hash
from config import Config
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def get_db():
    """Get a database connection for the current request context."""
    if "db" not in g:
        Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        # Enable WAL mode for high performance and foreign keys
        g.db.execute("PRAGMA journal_mode = WAL;")
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection if it exists."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Helper to query the database and return dictionary rows."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Helper to execute an INSERT/UPDATE/DELETE query and return lastrowid."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def init_db():
    """Initialize database tables using schema.sql."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    # We create a standalone connection for initialization
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

def generate_sample_image(filename, text, subtext, color="#10b981", folder="complaints"):
    """Generate a clean visual demo image file with text overlay if missing."""
    target_folder = Config.UPLOAD_FOLDER if folder == "complaints" else Config.PROOFS_FOLDER
    target_folder.mkdir(parents=True, exist_ok=True)
    file_path = target_folder / filename
    if file_path.exists():
        return f"{folder}/{filename}"
        
    width, height = 800, 500
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    
    # Draw geometric patterns/header
    draw.rectangle([0, 0, width, 80], fill="#047857")
    draw.text((30, 28), "CleanCity AI - Municipal Waste Inspection", fill="#ffffff")
    
    # Draw central placeholder banner
    draw.rounded_rectangle([40, 110, width - 40, height - 40], radius=16, fill="#ffffff")
    draw.text((70, 150), text, fill="#0f172a")
    draw.text((70, 200), subtext, fill="#475569")
    draw.text((70, 270), "Status: Verified System Demonstration Sample", fill="#059669")
    draw.text((70, 310), f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill="#64748b")
    draw.text((70, 360), "Camera: Smart Sanitation Mobile Unit", fill="#94a3b8")
    
    img.save(file_path, "JPEG")
    return f"{folder}/{filename}"

def seed_data():
    """Populate database with rich demonstration data if empty."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) AS cnt FROM users")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    print("Seeding CleanCity AI with sample users, workers, and complaints...")
    
    # 1. Seed Users
    # Admin
    admin_pw = generate_password_hash("Admin@123")
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, address)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Municipal Director Vance", "admin@cleancity.ai", admin_pw, "admin", "+1-555-0199", "City Hall, 100 Civic Center Plaza"))
    admin_id = cursor.lastrowid
    
    # Workers
    worker_pw = generate_password_hash("Worker@123")
    workers_data = [
        ("Marcus Vance", "worker1@cleancity.ai", "+1-555-0101", "Downtown Sector 4", "Garbage Truck A-12"),
        ("Elena Rostova", "worker2@cleancity.ai", "+1-555-0102", "North Riverside", "Recycling Compactor C-04"),
        ("Carlos Mendez", "worker3@cleancity.ai", "+1-555-0103", "Westside Boulevard", "Rapid Clearance Van V-09"),
        ("Aisha Khan", "worker4@cleancity.ai", "+1-555-0104", "Tech Park & Metro", "Heavy Duty Loader L-02")
    ]
    
    worker_records = []
    for w_name, w_email, w_phone, w_zone, w_veh in workers_data:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (w_name, w_email, worker_pw, "worker", w_phone, f"{w_zone} Depot"))
        u_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO workers (user_id, full_name, phone, zone, status, vehicle_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (u_id, w_name, w_phone, w_zone, "Available", w_veh))
        worker_records.append((cursor.lastrowid, u_id, w_name))

    # Citizens
    citizen_pw = generate_password_hash("Citizen@123")
    citizens_data = [
        ("Alice Green", "citizen@cleancity.ai", "+1-555-0201", "442 Maple Lane, Downtown"),
        ("David Chen", "citizen2@cleancity.ai", "+1-555-0202", "18 Riverwalk Promenade"),
        ("Maya Patel", "citizen3@cleancity.ai", "+1-555-0203", "89 Oakridge Avenue")
    ]
    
    citizen_ids = []
    for c_name, c_email, c_phone, c_addr in citizens_data:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (c_name, c_email, citizen_pw, "citizen", c_phone, c_addr))
        citizen_ids.append(cursor.lastrowid)
        
    c1_id, c2_id, c3_id = citizen_ids

    # Generate demo placeholder images
    img1 = generate_sample_image("demo_plastic_bottles.jpg", "Plastic Waste Accumulation", "High density discarded bottles & bags blocking curb", "#0284c7")
    img2 = generate_sample_image("demo_food_waste.jpg", "Organic & Food Waste Overflow", "Decomposing biological matter creating severe odor", "#d97706")
    img3 = generate_sample_image("demo_mixed_dump.jpg", "Illegal Mixed Dump Site", "Construction rubble, cardboard, household clutter", "#dc2626")
    img4_before = generate_sample_image("demo_metal_scrap_before.jpg", "Discarded Metal Cans & Hardware", "Scrap metal debris on sidewalk corner", "#64748b")
    img4_after = generate_sample_image("demo_metal_scrap_after.jpg", "RESOLVED: Sidewalk Sanitized", "Curb thoroughly cleared and pressure washed", "#059669", folder="proofs")
    img5 = generate_sample_image("demo_paper_cartons.jpg", "Paper & Cardboard Stack", "Rain-damaged packaging boxes near transit stop", "#7c3aed")
    img6 = generate_sample_image("demo_hotspot_park.jpg", "Repeated Dumping Spot", "Overflowing park bin with dispersed wrappers", "#e11d48")

    # 2. Seed Complaints (Centering near NYC / Urban grid coordinates)
    # 40.7128, -74.0060 is NYC City Hall
    complaints_seed = [
        {
            "user_id": c1_id,
            "title": "Severe Plastic Waste Spill Near Central Plaza",
            "description": "Massive accumulation of plastic packaging, bottles, and grocery bags scattered across the pedestrian footpath.",
            "waste_type": "Plastic waste",
            "severity": "High",
            "status": "Pending",
            "address": "250 Broadway, Civic Center, New York, NY",
            "landmark": "Near City Hall Fountain East Gate",
            "lat": 40.7135,
            "lng": -74.0055,
            "ai_waste_type": "Plastic waste",
            "ai_severity": "High",
            "ai_confidence": 0.94,
            "ai_explanation": "Visual inspection reveals high density of polyethylene bags and single-use beverage containers obstructing pedestrian walkways. Moderate fire and drainage blockage hazard.",
            "ai_recommendation": "Dispatch standard plastics collection squad with baling bags. Recommend checking storm drain nearby.",
            "detected_items": ["PET water bottles", "Polythene shopping bags", "Styrofoam cups"],
            "image": img1,
            "created_days_ago": 1
        },
        {
            "user_id": c2_id,
            "title": "Decomposing Organic Waste Behind Food Alley",
            "description": "Restaurant food waste bins overflowing with rotten vegetables and organic refuse. Attracting stray animals and generating foul smell.",
            "waste_type": "Organic waste",
            "severity": "Critical",
            "status": "Assigned",
            "address": "88 Fulton Street, Financial District, New York, NY",
            "landmark": "Rear loading dock of Grand Spice Bazaar",
            "lat": 40.7088,
            "lng": -74.0042,
            "ai_waste_type": "Organic waste",
            "ai_severity": "Critical",
            "ai_confidence": 0.96,
            "ai_explanation": "Extensive decomposition of organic vegetable and food matter with active liquid runoff. High biohazard and pest attraction score.",
            "ai_recommendation": "Immediate priority wet-waste collection required. Deploy disinfectant spray post-collection.",
            "detected_items": ["Decomposing food scraps", "Rotting fruit crates", "Organic grease effluent"],
            "image": img2,
            "worker_idx": 0,
            "created_days_ago": 2
        },
        {
            "user_id": c3_id,
            "title": "Repeated Illegal Mixed Dumping in Empty Lot",
            "description": "Chronic hotspot. Commercial and residential mixed rubbish discarded along the boundary wall overnight.",
            "waste_type": "Mixed waste",
            "severity": "Critical",
            "status": "In Progress",
            "address": "15 Chatham Square, Chinatown, New York, NY",
            "landmark": "Opposite Kimlau War Memorial",
            "lat": 40.7132,
            "lng": -73.9984,
            "ai_waste_type": "Mixed waste",
            "ai_severity": "Critical",
            "ai_confidence": 0.91,
            "ai_explanation": "Multiple material streams observed including broken timber, plastic buckets, electronic wire casing, and household waste. High volume > 3 cubic meters.",
            "ai_recommendation": "Requires mechanical compactor truck and multi-person crew. Surveillance camera recommended for repeated dumping deterrent.",
            "detected_items": ["Broken furniture", "PVC pipes", "Dry packaging", "Household trash"],
            "image": img3,
            "worker_idx": 1,
            "created_days_ago": 3
        },
        {
            "user_id": c1_id,
            "title": "Hazardous Metal Cans & Scraps Cleared from Corner",
            "description": "Sharp metal scrap discarded near school walkway. Successfully cleaned and collected.",
            "waste_type": "Metal waste",
            "severity": "Medium",
            "status": "Resolved",
            "address": "45 Wall Street, Financial District, New York, NY",
            "landmark": "Near Historic Federal Hall steps",
            "lat": 40.7069,
            "lng": -74.0090,
            "ai_waste_type": "Metal waste",
            "ai_severity": "Medium",
            "ai_confidence": 0.89,
            "ai_explanation": "Aluminum beverage cans and discarded steel sheet segments. Laceration hazard for pedestrians and pets.",
            "ai_recommendation": "Metal recycling segregation container. Protective leather gloves mandatory for crew.",
            "detected_items": ["Aluminum soda cans", "Tin food cans", "Galvanized wire cutoffs"],
            "image": img4_before,
            "after_image": img4_after,
            "worker_idx": 2,
            "created_days_ago": 4,
            "resolved_days_ago": 1
        },
        {
            "user_id": c2_id,
            "title": "Wet Cardboard Cartons Collapsed at Bus Shelter",
            "description": "Commercial delivery boxes dumped and soaked after morning rain, obstructing commuters.",
            "waste_type": "Paper waste",
            "severity": "Low",
            "status": "Pending",
            "address": "120 Broadway, Manhattan, NY",
            "landmark": "Equitable Building North Bus Stop",
            "lat": 40.7099,
            "lng": -74.0105,
            "ai_waste_type": "Paper waste",
            "ai_severity": "Low",
            "ai_confidence": 0.95,
            "ai_explanation": "Flattened corrugated cardboard sheets with moisture absorption. Non-hazardous, dry/paper recycling eligible once dried.",
            "ai_recommendation": "Standard dry recycling collection van.",
            "detected_items": ["Corrugated cardboard boxes", "Shipping labels", "Packaging paper"],
            "image": img5,
            "created_days_ago": 0
        },
        # Hotspot complaints clustered around Chatham Square to demonstrate Hotspot Detection
        {
            "user_id": c3_id,
            "title": "Secondary Trash Accumulation at Chatham Corner",
            "description": "More bags dumped within 50 meters of the primary Chinatown empty lot hotspot.",
            "waste_type": "Plastic waste",
            "severity": "High",
            "status": "Assigned",
            "address": "19 Chatham Square, Chinatown, New York, NY",
            "landmark": "Beside Postal Sub-station",
            "lat": 40.7136,
            "lng": -73.9981,
            "ai_waste_type": "Plastic waste",
            "ai_severity": "High",
            "ai_confidence": 0.92,
            "ai_explanation": "Plastic takeaway containers and drink cups accumulating rapidly. Indicates localized spillover hotspot.",
            "ai_recommendation": "Deploy an additional public street bin at this intersection.",
            "detected_items": ["Plastic takeout containers", "Polystyrene trays", "Coffee lids"],
            "image": img6,
            "worker_idx": 1,
            "created_days_ago": 2
        },
        {
            "user_id": c1_id,
            "title": "Littering at Chinatown Memorial Plaza",
            "description": "Recurring plastic bags and cups blown against perimeter fence.",
            "waste_type": "Mixed waste",
            "severity": "Medium",
            "status": "Pending",
            "address": "12 Chatham Square, Chinatown, New York, NY",
            "landmark": "Kimlau Memorial Plaza North Gate",
            "lat": 40.7130,
            "lng": -73.9988,
            "ai_waste_type": "Mixed waste",
            "ai_severity": "Medium",
            "ai_confidence": 0.88,
            "ai_explanation": "Dispersed litter across plaza perimeter. High public visibility.",
            "ai_recommendation": "Routine street sweep patrol and community cleanup notice.",
            "detected_items": ["Snack wrappers", "Disposable water bottles", "Flyers"],
            "image": img1,
            "created_days_ago": 1
        }
    ]

    for c in complaints_seed:
        created_time = datetime.now() - timedelta(days=c["created_days_ago"])
        cursor.execute("""
            INSERT INTO complaints (
                user_id, title, description, waste_type, severity, status,
                address, landmark, latitude, longitude,
                ai_waste_type, ai_severity, ai_confidence,
                ai_explanation, ai_recommendation, ai_detected_items,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["user_id"], c["title"], c["description"], c["waste_type"], c["severity"], c["status"],
            c["address"], c["landmark"], c["lat"], c["lng"],
            c["ai_waste_type"], c["ai_severity"], c["ai_confidence"],
            c["ai_explanation"], c["ai_recommendation"], json.dumps(c["detected_items"]),
            created_time.strftime("%Y-%m-%d %H:%M:%S"), created_time.strftime("%Y-%m-%d %H:%M:%S")
        ))
        comp_id = cursor.lastrowid

        # Insert 'before' image
        cursor.execute("""
            INSERT INTO complaint_images (complaint_id, image_type, file_path, caption, uploaded_at)
            VALUES (?, 'before', ?, ?, ?)
        """, (comp_id, c["image"], "Initial citizen photo submission", created_time.strftime("%Y-%m-%d %H:%M:%S")))

        # If assigned / in progress / resolved, create assignment and status history
        if "worker_idx" in c:
            w_id, _, w_name = worker_records[c["worker_idx"]]
            assign_time = created_time + timedelta(hours=3)
            comp_status = "Completed" if c["status"] == "Resolved" else c["status"]
            completed_time = (datetime.now() - timedelta(days=c.get("resolved_days_ago", 1))).strftime("%Y-%m-%d %H:%M:%S") if c["status"] == "Resolved" else None
            
            cursor.execute("""
                INSERT INTO assignments (complaint_id, worker_id, assigned_by, assigned_at, status, notes, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (comp_id, w_id, admin_id, assign_time.strftime("%Y-%m-%d %H:%M:%S"), comp_status, f"Assigned to {w_name} for cleanup.", completed_time))

            # If resolved, add 'after' image
            if c["status"] == "Resolved" and "after_image" in c:
                cursor.execute("""
                    INSERT INTO complaint_images (complaint_id, image_type, file_path, caption, uploaded_at)
                    VALUES (?, 'after', ?, ?, ?)
                """, (comp_id, c["after_image"], "Cleaned site verified by sanitation worker", completed_time))

        # Initial status history
        cursor.execute("""
            INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes, created_at)
            VALUES (?, ?, NULL, 'Pending', 'Complaint filed by citizen.', ?)
        """, (comp_id, c["user_id"], created_time.strftime("%Y-%m-%d %H:%M:%S")))

        if c["status"] in ["Assigned", "In Progress", "Resolved"]:
            cursor.execute("""
                INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes, created_at)
                VALUES (?, ?, 'Pending', 'Assigned', 'Assigned to municipal field squad.', ?)
            """, (comp_id, admin_id, (created_time + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")))

        if c["status"] in ["In Progress", "Resolved"]:
            cursor.execute("""
                INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes, created_at)
                VALUES (?, ?, 'Assigned', 'In Progress', 'Field unit en route to site.', ?)
            """, (comp_id, admin_id, (created_time + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")))

        if c["status"] == "Resolved":
            cursor.execute("""
                INSERT INTO status_history (complaint_id, changed_by, old_status, new_status, notes, created_at)
                VALUES (?, ?, 'In Progress', 'Resolved', 'Waste cleared and documented with proof.', ?)
            """, (comp_id, admin_id, completed_time))

    conn.commit()
    conn.close()
    print("CleanCity AI seeded successfully.")
