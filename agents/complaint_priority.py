import math
from datetime import datetime
from database.db import query_db

def calculate_priority_score(complaint, nearby_count=0):
    """
    Calculate an intelligent composite priority index (0 - 100) for municipal triage.
    Higher score indicates higher dispatch urgency.
    """
    score = 0
    
    # 1. Severity weight (max 40 pts)
    severity_weights = {
        "Critical": 40,
        "High": 30,
        "Medium": 20,
        "Low": 10
    }
    score += severity_weights.get(complaint.get("severity", "Medium"), 20)
    
    # 2. Waste Hazard Profile (max 25 pts)
    waste_weights = {
        "Organic waste": 25,  # High vector disease & odor risk
        "Mixed waste": 22,
        "Plastic waste": 18,  # Drainage choke & fire risk
        "Metal waste": 16,    # Sharp injury risk
        "Paper waste": 10,
        "Other waste": 15
    }
    score += waste_weights.get(complaint.get("waste_type", "Mixed waste"), 15)
    
    # 3. Hotspot / Recurring Density Bonus (max 20 pts)
    # If this location is within a chronic hotspot zone
    if nearby_count >= 3:
        score += 20
    elif nearby_count >= 1:
        score += 10
        
    # 4. Aging / SLA Elapsed Time (max 15 pts)
    created_at = complaint.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                dt = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
            else:
                dt = created_at
            hours_elapsed = (datetime.now() - dt).total_seconds() / 3600.0
            if hours_elapsed > 48:
                score += 15
            elif hours_elapsed > 24:
                score += 8
            elif hours_elapsed > 12:
                score += 4
        except Exception:
            pass

    score = min(100, max(5, score))
    
    # Generate action badge
    if score >= 80:
        badge = {"label": "Emergency Priority", "color": "danger", "sla_hours": 4}
    elif score >= 60:
        badge = {"label": "High Priority", "color": "warning", "sla_hours": 12}
    elif score >= 40:
        badge = {"label": "Standard Municipal", "color": "info", "sla_hours": 24}
    else:
        badge = {"label": "Routine Patrol", "color": "secondary", "sla_hours": 48}
        
    return {
        "priority_score": score,
        "badge_label": badge["label"],
        "badge_color": badge["color"],
        "target_sla_hours": badge["sla_hours"]
    }

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in meters."""
    if None in (lat1, lon1, lat2, lon2):
        return 9999999.0
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_hotspots(threshold_meters=300, min_complaints=2):
    """
    Cluster active complaints into localized garbage hotspots.
    Returns clusters with center lat/lng, count, and radius.
    """
    complaints = query_db("""
        SELECT id, title, latitude, longitude, severity, waste_type, address, status, created_at
        FROM complaints
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY created_at DESC
    """)
    
    clusters = []
    visited = set()
    
    for i, c1 in enumerate(complaints):
        if c1["id"] in visited:
            continue
            
        cluster_members = [c1]
        visited.add(c1["id"])
        
        for j, c2 in enumerate(complaints):
            if c2["id"] in visited:
                continue
            dist = haversine_distance_meters(
                c1["latitude"], c1["longitude"],
                c2["latitude"], c2["longitude"]
            )
            if dist <= threshold_meters:
                cluster_members.append(c2)
                visited.add(c2["id"])
                
        if len(cluster_members) >= min_complaints:
            avg_lat = sum(c["latitude"] for c in cluster_members) / len(cluster_members)
            avg_lng = sum(c["longitude"] for c in cluster_members) / len(cluster_members)
            critical_count = sum(1 for c in cluster_members if c["severity"] in ("Critical", "High"))
            
            clusters.append({
                "center_lat": round(avg_lat, 6),
                "center_lng": round(avg_lng, 6),
                "complaints_count": len(cluster_members),
                "critical_count": critical_count,
                "radius_meters": threshold_meters,
                "address_sample": cluster_members[0]["address"] or "Recurring Municipal Sector",
                "member_ids": [c["id"] for c in cluster_members],
                "risk_level": "High Hotspot" if critical_count >= 2 else "Moderate Hotspot"
            })
            
    return clusters
