import unittest
from app import create_app

class RouteSmokeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_public_routes(self):
        routes = ["/", "/map", "/login", "/register"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Route {r} failed with status {resp.status_code}")

    def test_citizen_routes(self):
        # Login as citizen
        self.client.post("/login", data={"email": "citizen@cleancity.ai", "password": "Citizen@123"})
        routes = ["/citizen/dashboard", "/citizen/report", "/citizen/complaints", "/citizen/complaint/1"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Citizen route {r} failed with status {resp.status_code}")

    def test_worker_routes(self):
        # Login as worker
        self.client.post("/login", data={"email": "worker1@cleancity.ai", "password": "Worker@123"})
        routes = ["/worker/dashboard"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Worker route {r} failed with status {resp.status_code}")

    def test_admin_routes(self):
        # Login as admin
        self.client.post("/login", data={"email": "admin@cleancity.ai", "password": "Admin@123"})
        routes = ["/admin/dashboard", "/admin/map", "/admin/analytics", "/admin/workers"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Admin route {r} failed with status {resp.status_code}")

if __name__ == "__main__":
    unittest.main()
