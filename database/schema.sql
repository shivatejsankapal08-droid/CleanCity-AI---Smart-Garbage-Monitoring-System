-- CleanCity AI Database Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('citizen', 'admin', 'worker')),
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    waste_type TEXT DEFAULT 'Mixed waste',
    severity TEXT DEFAULT 'Medium' CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Assigned', 'In Progress', 'Resolved', 'Rejected')),
    address TEXT,
    landmark TEXT,
    latitude REAL,
    longitude REAL,
    ai_waste_type TEXT,
    ai_severity TEXT,
    ai_confidence REAL DEFAULT 0.0,
    ai_explanation TEXT,
    ai_recommendation TEXT,
    ai_detected_items TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone TEXT,
    zone TEXT NOT NULL,
    status TEXT DEFAULT 'Available' CHECK(status IN ('Available', 'Busy', 'Off-Duty')),
    vehicle_type TEXT DEFAULT 'Garbage Truck',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Assigned' CHECK(status IN ('Assigned', 'In Progress', 'Completed', 'Cancelled')),
    notes TEXT,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaint_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    image_type TEXT NOT NULL CHECK(image_type IN ('before', 'after')),
    file_path TEXT NOT NULL,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    changed_by INTEGER REFERENCES users(id),
    old_status TEXT,
    new_status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON complaints(user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_coords ON complaints(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_assignments_worker ON assignments(worker_id);
CREATE INDEX IF NOT EXISTS idx_assignments_complaint ON assignments(complaint_id);
CREATE INDEX IF NOT EXISTS idx_complaint_images_complaint ON complaint_images(complaint_id);
