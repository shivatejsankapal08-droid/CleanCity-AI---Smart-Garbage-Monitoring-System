import os
import sys
import unittest
from io import BytesIO
from PIL import Image
from app import create_app
from database.db import query_db, Config

class CleanCitySystemTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_database_seeded_properly(self):
        with self.app.app_context():
            admin = query_db("SELECT * FROM users WHERE email = 'admin@cleancity.ai'", one=True)
            self.assertIsNotNone(admin, "Admin user should exist")
            self.assertEqual(admin["role"], "admin")

            workers = query_db("SELECT * FROM workers")
            self.assertGreaterEqual(len(workers), 3, "At least 3 workers should be seeded")

            complaints = query_db("SELECT * FROM complaints")
            self.assertGreaterEqual(len(complaints), 5, "At least 5 complaints should be seeded")

    def test_02_authentication_and_roles(self):
        # 1. Failed login
        resp = self.client.post("/login", data={
            "email": "admin@cleancity.ai",
            "password": "WrongPassword123"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", resp.data)

        # 2. Successful Admin login
        resp_admin = self.client.post("/login", data={
            "email": "admin@cleancity.ai",
            "password": "Admin@123"
        }, follow_redirects=True)
        self.assertIn(b"Municipal Command Center", resp_admin.data)

        # 3. Successful Worker login
        self.client.get("/logout")
        resp_worker = self.client.post("/login", data={
            "email": "worker1@cleancity.ai",
            "password": "Worker@123"
        }, follow_redirects=True)
        self.assertIn(b"Sanitation Field Operations", resp_worker.data)

        # 4. Successful Citizen login
        self.client.get("/logout")
        resp_citizen = self.client.post("/login", data={
            "email": "citizen@cleancity.ai",
            "password": "Citizen@123"
        }, follow_redirects=True)
        self.assertIn(b"Citizen Portal", resp_citizen.data)

    def test_03_citizen_complaint_submission_with_ai(self):
        # Login as citizen
        self.client.post("/login", data={
            "email": "citizen@cleancity.ai",
            "password": "Citizen@123"
        })

        # Create in-memory test image
        img_io = BytesIO()
        test_img = Image.new("RGB", (300, 300), color="blue")
        test_img.save(img_io, "JPEG")
        img_io.seek(0)

        # Submit complaint
        data = {
            "title": "Automated Unit Test - Plastic Bottles in Park",
            "description": "Cluster of plastic mineral water bottles discarded next to bench.",
            "latitude": "40.7140",
            "longitude": "-74.0070",
            "address": "City Hall Park North Lawn",
            "landmark": "Near reading pavilion",
            "garbage_photo": (img_io, "test_plastic_dump.jpg")
        }

        resp = self.client.post("/citizen/report", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AI Waste Diagnostics", resp.data)
        self.assertIn(b"Automated Unit Test", resp.data)

        # Verify in database
        with self.app.app_context():
            new_comp = query_db("SELECT * FROM complaints WHERE title = ?", ["Automated Unit Test - Plastic Bottles in Park"], one=True)
            self.assertIsNotNone(new_comp)
            self.assertIn(new_comp["waste_type"], Config.WASTE_CATEGORIES)
            self.assertIn(new_comp["severity"], Config.SEVERITY_LEVELS)

    def test_04_admin_dispatch_and_status(self):
        # Login as admin
        self.client.post("/login", data={
            "email": "admin@cleancity.ai",
            "password": "Admin@123"
        })

        with self.app.app_context():
            pending = query_db("SELECT id FROM complaints WHERE status = 'Pending' LIMIT 1", one=True)
            self.assertIsNotNone(pending)
            comp_id = pending["id"]

        # Assign worker
        resp = self.client.post("/admin/assign", data={
            "complaint_id": comp_id,
            "worker_id": 1,
            "assignment_notes": "Unit test assignment"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            updated = query_db("SELECT status FROM complaints WHERE id = ?", [comp_id], one=True)
            self.assertEqual(updated["status"], "Assigned")

        # Update status directly
        resp2 = self.client.post("/admin/status/update", data={
            "complaint_id": comp_id,
            "status": "In Progress",
            "notes": "Admin test transition"
        }, follow_redirects=True)
        self.assertEqual(resp2.status_code, 200)

        with self.app.app_context():
            updated2 = query_db("SELECT status FROM complaints WHERE id = ?", [comp_id], one=True)
            self.assertEqual(updated2["status"], "In Progress")

    def test_05_worker_task_completion_with_proof(self):
        # Login as worker
        self.client.post("/login", data={
            "email": "worker1@cleancity.ai",
            "password": "Worker@123"
        })

        with self.app.app_context():
            task = query_db("""
                SELECT c.id FROM complaints c
                JOIN assignments a ON c.id = a.complaint_id
                WHERE a.worker_id = 1 AND c.status IN ('Assigned', 'In Progress')
                LIMIT 1
            """, one=True)
            self.assertIsNotNone(task, "Worker 1 should have an assigned task")
            task_id = task["id"]

        # Create proof image
        proof_io = BytesIO()
        proof_img = Image.new("RGB", (300, 300), color="green")
        proof_img.save(proof_io, "JPEG")
        proof_io.seek(0)

        # Complete task
        resp = self.client.post(f"/worker/task/{task_id}/complete", data={
            "completion_notes": "Site thoroughly cleaned and sanitized. Test passed.",
            "after_photo": (proof_io, "test_proof.jpg")
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            resolved = query_db("SELECT status FROM complaints WHERE id = ?", [task_id], one=True)
            self.assertEqual(resolved["status"], "Resolved")
            
            # Check after image in database
            after_img = query_db("SELECT * FROM complaint_images WHERE complaint_id = ? AND image_type = 'after'", [task_id], one=True)
            self.assertIsNotNone(after_img, "After proof image should be recorded")

    def test_06_apis_and_hotspots(self):
        # 1. Map data API
        resp_map = self.client.get("/admin/api/map-data")
        self.assertEqual(resp_map.status_code, 200)
        data = resp_map.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(len(data["markers"]), 0)
        self.assertGreater(len(data["hotspots"]), 0, "Hotspots should be detected from clustered coordinates")

        # 2. Analytics data API
        resp_ana = self.client.get("/admin/api/analytics-data")
        self.assertEqual(resp_ana.status_code, 200)
        data_ana = resp_ana.get_json()
        self.assertIn("waste", data_ana)
        self.assertIn("severity", data_ana)
        self.assertIn("status", data_ana)

if __name__ == "__main__":
    unittest.main()
