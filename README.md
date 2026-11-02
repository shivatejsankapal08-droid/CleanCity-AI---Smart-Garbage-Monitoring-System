# CleanCity AI – AI-Powered Smart Garbage Monitoring and Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.x-green.svg)](https://palletsprojects.com/p/flask/)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20Vision-purple.svg)](https://aistudio.google.com/)
[![Maps](https://img.shields.io/badge/Maps-Leaflet%20%26%20OpenStreetMap-orange.svg)](https://leafletjs.com/)
[![Charts](https://img.shields.io/badge/Analytics-Chart.js-yellow.svg)](https://www.chartjs.org/)

**CleanCity AI** is an enterprise-grade municipal solid-waste surveillance, complaint triage, and sanitation dispatch platform. It bridges citizens, municipal administration, and sanitation field workers through autonomous multimodal AI vision classification, geospatial hotspot clustering, and proof-of-work verification.

---

## 🌟 Key Highlights & Capabilities

### Module 1: Citizen Dashboard & Reporting
* **Photo Capture & Upload:** Citizens upload photographs of garbage piles with real-time browser preview and strict format/size validation.
* **Interactive Leaflet Location Picker:** Drag-and-drop map pin, click-to-place coordinates, or 1-click **HTML5 GPS Geolocation** with automatic reverse geocoding via OpenStreetMap.
* **Complaint Tracking:** Live lifecycle tracker (Pending &rarr; Assigned &rarr; In Progress &rarr; Resolved).
* **Proof-of-Cleanliness Verification:** Citizens can inspect the original photo alongside the sanitation worker's verified after-cleaning photograph.

### Module 2: AI Garbage Detection (Gemini Multimodal Vision)
* **Autonomous Visual Classification:** Analyzes uploaded images and categorizes waste strictly into:
  1. `Organic waste`
  2. `Plastic waste`
  3. `Paper waste`
  4. `Metal waste`
  5. `Mixed waste`
  6. `Other waste`
* **Severity Estimation:** Low, Medium, High, and Critical hazard levels based on volume, pathway blockage, and vector risks.
* **AI Visual Explanation:** Environmental risk breakdown and detected items inventory.
* **Actionable Recommendations:** Suggests required crew equipment (e.g., compaction trucks, puncture-proof gloves, biological disinfectant).
* **Resilient Heuristic Fallback Engine:** If no `GEMINI_API_KEY` is provided or if network connectivity is offline, the system automatically falls back to an intelligent autonomous vision heuristic that guarantees complete functionality without throwing 500 errors.

### Module 3: Geospatial Location Management & Hotspot Detection
* **OpenStreetMap & Leaflet Integration:** Live full-screen and mini-maps rendering city-wide complaints.
* **Severity Color Pins:** Color-coded markers (Critical: Red, High: Orange, Medium: Amber, Resolved: Emerald Green).
* **Algorithmic Hotspot Clustering:** Uses the **Haversine formula** to detect repeated garbage dumping within a 300-meter radius, rendering pulsing danger zones to alert municipal planners where additional bins or cameras are needed.

### Module 4: Municipal Admin Dashboard
* **Real-Time KPI Counters:** Total volume, pending triage, active dispatches, and resolution rate percentages.
* **Intelligent Worker Dispatch:** Assign complaints to sanitation workers based on assigned sector/zone and active workload.
* **Status Audit Trails:** Every status transition is logged with timestamp, user ID, and administrative notes.
* **Sanitation Fleet Management:** Oversee active workers, toggle duty status, and balance task distribution.

### Module 5: Field Worker Dashboard
* **Worker Dispatch Roster:** Field personnel log in to see urgent assigned tasks sorted by severity.
* **GPS Routing:** 1-click directions to the exact complaint coordinates.
* **Proof of Work (PoC):** Workers mark tasks "In Progress", execute cleanup, upload an **after-cleaning photograph**, and log completion notes to mark tasks "Resolved".

### Module 6: Smart Municipal Analytics
* **Waste Category Breakdown:** Interactive Chart.js Doughnut chart showing distribution of plastics, organics, metals, and recyclables.
* **Hazard Severity Index:** Bar chart illustrating critical vs routine complaints.
* **Monthly Influx Trends:** Curved line graph showing complaint volume over time.
* **Hotspot Leaderboard:** Chronic dump site table with coordinates, risk levels, and cluster sizes.

---

## 🏗️ Project Architecture

```
CleanCity AI – Smart Garbage Monitoring System/
│
├── app.py                     # Flask application factory, routes, and startup seed
├── config.py                  # Environment config, paths, and allowed extensions
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Local environment configuration
│
├── database/
│   ├── db.py                  # SQLite WAL connection manager & rich demo seeder
│   └── schema.sql             # Relational schema (users, complaints, workers, assignments, images, history)
│
├── agents/
│   ├── garbage_detection.py   # Gemini AI vision analyzer + heuristic fallback engine
│   └── complaint_priority.py  # Composite priority index & Haversine hotspot clusterer
│
├── routes/
│   ├── auth.py                # Authentication, sessions, role decorators, quick-login
│   ├── citizen.py             # Citizen dashboard, complaint filing, photo upload
│   ├── admin.py               # Municipal command center, worker dispatch, status updates, analytics API
│   └── worker.py              # Field operations, task progress, after-photo upload proof
│
├── templates/
│   ├── base.html              # Modern green & white eco smart-city master layout
│   ├── landing.html           # Public landing page with live statistics and demo cards
│   ├── login.html             # Login with 1-click instant demo credentials
│   ├── register.html          # Citizen & field worker registration
│   ├── citizen_dashboard.html # Citizen statistics and complaint tracking
│   ├── report_garbage.html    # Complaint submission with Leaflet GPS picker
│   ├── complaints.html        # Filterable complaints registry
│   ├── complaint_detail.html  # Diagnostic deep dive, before/after photos, timeline
│   ├── admin_dashboard.html   # Municipal triage table and dispatch modals
│   ├── worker_dashboard.html  # Field worker task queue and proof upload
│   ├── map.html               # Full interactive Leaflet map & hotspot clusters
│   ├── analytics.html         # Chart.js analytics graphs & hotspot leaderboard
│   ├── workers.html           # Sanitation fleet roster management
│   └── 404.html               # Clean 404 error page
│
├── static/
│   ├── css/
│   │   └── style.css          # Eco-smart city design system (Emerald green, slate, cards)
│   ├── js/
│   │   └── main.js            # Leaflet map pins, GPS locator, image previews, modals
│   └── uploads/
│       ├── complaints/        # Citizen uploaded 'before' photos
│       └── proofs/            # Worker uploaded 'after' proof photos
│
└── README.md                  # System manual and documentation
```

---

## 🚀 Installation & Execution

### 1. Prerequisites
- Python 3.10+ (Verified on Python 3.14.5)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 2. Install Dependencies
In the project directory, run:
```bash
pip install -r requirements.txt
```

### 3. Configure Gemini AI API Key (Optional)
The system runs completely out-of-the-box in autonomous fallback mode. To activate live Google Gemini Multimodal inference:
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Open `.env` and set:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Start the CleanCity AI Server
Run the Flask server:
```bash
python app.py
```

Open your browser at:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Pre-Seeded Demonstration Accounts

CleanCity AI automatically initializes and seeds an SQLite database (`database/cleancity.db`) with realistic complaints, images, and accounts. You can sign in instantly using the demo buttons on the login page, or manually with:

| Role | Email Address | Password | Description |
| :--- | :--- | :--- | :--- |
| **Municipal Administrator** | `admin@cleancity.ai` | `Admin@123` | Full access to dispatch, status updates, analytics, and fleet roster |
| **Sanitation Worker 1** | `worker1@cleancity.ai` | `Worker@123` | Marcus Vance (Downtown Sector 4, Truck A-12) |
| **Sanitation Worker 2** | `worker2@cleancity.ai` | `Worker@123` | Elena Rostova (North Riverside, Compactor C-04) |
| **Citizen Reporter** | `citizen@cleancity.ai` | `Citizen@123` | Alice Green (Pre-seeded with complaints in different lifecycle stages) |
| **Citizen Reporter 2** | `citizen2@cleancity.ai` | `Citizen@123` | David Chen |

---

## 🔒 Security & Data Integrity

- **Password Security:** Salted hashes generated and verified via `werkzeug.security`.
- **Role-Based Access Control (RBAC):** Decorators `@login_required` and `@role_required(['admin'])` protect all administrative and operational endpoints.
- **File Upload Protection:** Secure filename generation using UUIDs, content length capped at 16MB, and strict MIME/extension whitelisting (`.jpg`, `.jpeg`, `.png`, `.webp`).
- **SQL Injection Prevention:** 100% parameterized queries via Python SQLite3.
- **Resilient AI Execution:** Graceful exception handling with fallback detection when API quotas or internet disruptions occur.

---

## 🌿 CleanCity AI – Building Cleaner, Smarter Cities Together
Developed with Python Flask, Google Gemini AI, Leaflet, and Chart.js.
