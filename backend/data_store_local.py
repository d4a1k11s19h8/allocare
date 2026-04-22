"""
data_store_local.py — Local JSON-file Data Store for Render/non-Firebase Deployment
Same API as the Firestore-backed DataStore so main.py works unchanged.
"""
import os
import uuid
import json
import logging
import hashlib
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"


class DataStore:
    """JSON-file-backed document store — drop-in replacement for Firestore version."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}
        self._load()

    def _load(self):
        """Load data from JSON file."""
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(f"[DataStore-Local] Loaded data from {DATA_FILE}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[DataStore-Local] Could not load {DATA_FILE}: {e}")
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        """Persist data to JSON file."""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"[DataStore-Local] Could not save {DATA_FILE}: {e}")

    def add(self, collection: str, data: dict, doc_id: str = None) -> str:
        with self._lock:
            if collection not in self._data:
                self._data[collection] = {}
            doc_id = doc_id or str(uuid.uuid4())[:20]
            data["_id"] = doc_id
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc).isoformat()
            self._data[collection][doc_id] = data
            self._save()
            return doc_id

    def get(self, collection: str, doc_id: str) -> Optional[dict]:
        return self._data.get(collection, {}).get(doc_id)

    def update(self, collection: str, doc_id: str, updates: dict) -> bool:
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id in col:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                col[doc_id].update(updates)
                self._save()
                return True
            return False

    def delete(self, collection: str, doc_id: str) -> bool:
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id in col:
                del col[doc_id]
                self._save()
                return True
            return False

    def list_all(self, collection: str) -> List[dict]:
        return list(self._data.get(collection, {}).values())

    def query(
        self,
        collection: str,
        filters: Dict[str, Any] = None,
        order_by: str = None,
        descending: bool = False,
        limit: int = 100,
    ) -> List[dict]:
        docs = list(self._data.get(collection, {}).values())

        # Apply filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    docs = [d for d in docs if d.get(key) in value]
                else:
                    docs = [d for d in docs if d.get(key) == value]

        # Sort
        if order_by:
            docs.sort(key=lambda d: d.get(order_by, 0) or 0, reverse=descending)

        return docs[:limit]

    def count(self, collection: str, filters: Dict[str, Any] = None) -> int:
        return len(self.query(collection, filters, limit=10000))

    def increment(self, collection: str, doc_id: str, field: str, amount: int = 1) -> bool:
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id in col:
                current = col[doc_id].get(field, 0) or 0
                col[doc_id][field] = current + amount
                self._save()
                return True
            return False

    def set_nested(self, collection: str, doc_id: str, path: str, value: Any) -> bool:
        """Set a nested field like 'impact_stats.total_tasks_completed'."""
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id in col:
                parts = path.split(".")
                obj = col[doc_id]
                for part in parts[:-1]:
                    if part not in obj or not isinstance(obj[part], dict):
                        obj[part] = {}
                    obj = obj[part]
                current = obj.get(parts[-1], 0) or 0
                obj[parts[-1]] = current + value
                self._save()
                return True
            return False

    def clear_collection(self, collection: str):
        with self._lock:
            self._data[collection] = {}
            self._save()

    def hash_password(self, password: str) -> str:
        """Simple SHA-256 hash for prototype authentication."""
        return hashlib.sha256(password.encode()).hexdigest()

    def seed_demo_data(self):
        """Load seed data if collections are empty."""
        needs = self.list_all("need_reports")
        if len(needs) > 0:
            logger.info("[DataStore-Local] Data already exists, skipping seed.")
            return

        logger.info("[DataStore-Local] Seeding demo data...")

        # ── Seed Volunteers ──────────────────────────────────
        volunteers = [
            {"display_name": "Priya Sharma", "email": "priya@example.com", "lat": 19.0450, "lng": 72.8570, "zone": "Dharavi", "skills": ["food distribution", "medical first aid", "hindi speaking"], "status": "available", "impact_points": 580, "impact_stats": {"total_tasks_completed": 23, "total_people_helped": 456}, "max_distance_km": 10},
            {"display_name": "Rahul Deshmukh", "email": "rahul@example.com", "lat": 19.0730, "lng": 72.8790, "zone": "Kurla", "skills": ["construction", "plumbing", "electrical"], "status": "available", "impact_points": 320, "impact_stats": {"total_tasks_completed": 12, "total_people_helped": 180}, "max_distance_km": 10},
            {"display_name": "Anita Patel", "email": "anita@example.com", "lat": 19.0540, "lng": 72.9150, "zone": "Govandi", "skills": ["teaching", "counseling"], "status": "available", "impact_points": 680, "impact_stats": {"total_tasks_completed": 18, "total_people_helped": 540}, "max_distance_km": 15},
            {"display_name": "Mohammed Shaikh", "email": "mohammed@example.com", "lat": 19.0440, "lng": 72.8555, "zone": "Dharavi", "skills": ["cooking", "food distribution", "driving"], "status": "available", "impact_points": 1450, "impact_stats": {"total_tasks_completed": 45, "total_people_helped": 1200}, "max_distance_km": 12},
            {"display_name": "Sneha Nair", "email": "sneha@example.com", "lat": 19.1200, "lng": 72.8470, "zone": "Andheri East", "skills": ["nursing", "medical first aid", "patient care"], "status": "available", "impact_points": 890, "impact_stats": {"total_tasks_completed": 31, "total_people_helped": 620}, "max_distance_km": 15},
            {"display_name": "Vikram Singh", "email": "vikram@example.com", "lat": 19.1870, "lng": 72.8490, "zone": "Malad East", "skills": ["construction", "carpentry", "heavy lifting"], "status": "assigned", "impact_points": 210, "impact_stats": {"total_tasks_completed": 8, "total_people_helped": 85}, "max_distance_km": 10},
            {"display_name": "Fatima Khan", "email": "fatima@example.com", "lat": 19.0596, "lng": 72.8413, "zone": "Bandra East", "skills": ["social work", "counseling", "legal aid"], "status": "available", "impact_points": 420, "impact_stats": {"total_tasks_completed": 15, "total_people_helped": 275}, "max_distance_km": 12},
            {"display_name": "Arjun Mehta", "email": "arjun@example.com", "lat": 19.0620, "lng": 72.8980, "zone": "Chembur", "skills": ["pharmacy", "medical first aid", "data entry"], "status": "available", "impact_points": 250, "impact_stats": {"total_tasks_completed": 10, "total_people_helped": 150}, "max_distance_km": 10},
            {"display_name": "Ravi Kumar", "email": "ravi@example.com", "lat": 19.0404, "lng": 72.8625, "zone": "Sion", "skills": ["driving", "food distribution", "logistics"], "status": "available", "impact_points": 1100, "impact_stats": {"total_tasks_completed": 35, "total_people_helped": 900}, "max_distance_km": 20},
            {"display_name": "Kavitha Reddy", "email": "kavitha@example.com", "lat": 19.0197, "lng": 72.8440, "zone": "Dadar", "skills": ["medical doctor", "patient care"], "status": "available", "impact_points": 340, "impact_stats": {"total_tasks_completed": 8, "total_people_helped": 160}, "max_distance_km": 15},
            {"display_name": "Tushar Patil", "email": "tushar@example.com", "lat": 19.0088, "lng": 72.8175, "zone": "Worli", "skills": ["civil engineering", "structural assessment"], "status": "available", "impact_points": 190, "impact_stats": {"total_tasks_completed": 6, "total_people_helped": 120}, "max_distance_km": 10},
            {"display_name": "Hassan Ali", "email": "hassan@example.com", "lat": 19.2045, "lng": 72.8400, "zone": "Kandivali", "skills": ["cooking", "food distribution", "event coordination"], "status": "available", "impact_points": 820, "impact_stats": {"total_tasks_completed": 28, "total_people_helped": 700}, "max_distance_km": 15},
            {"display_name": "Amit Deshmukh", "email": "amit.d@example.com", "lat": 21.1458, "lng": 79.0882, "zone": "Nagpur", "skills": ["construction", "heavy lifting", "disaster relief"], "status": "available", "impact_points": 720, "impact_stats": {"total_tasks_completed": 30, "total_people_helped": 500}, "max_distance_km": 20},
            {"display_name": "Sunita Wankhede", "email": "sunita.w@example.com", "lat": 21.1520, "lng": 79.0750, "zone": "Nagpur", "skills": ["nursing", "medical first aid", "patient care"], "status": "available", "impact_points": 560, "impact_stats": {"total_tasks_completed": 22, "total_people_helped": 380}, "max_distance_km": 15},
            {"display_name": "Rajesh Thakur", "email": "rajesh.t@example.com", "lat": 21.1400, "lng": 79.1000, "zone": "Nagpur", "skills": ["driving", "logistics", "food distribution"], "status": "available", "impact_points": 340, "impact_stats": {"total_tasks_completed": 14, "total_people_helped": 220}, "max_distance_km": 25},
            {"display_name": "Meena Bhonsle", "email": "meena.b@example.com", "lat": 21.1600, "lng": 79.0950, "zone": "Nagpur", "skills": ["social work", "counseling", "event coordination"], "status": "available", "impact_points": 480, "impact_stats": {"total_tasks_completed": 19, "total_people_helped": 310}, "max_distance_km": 15},
            {"display_name": "Arun Gupta", "email": "arun.g@example.com", "lat": 28.6280, "lng": 77.2170, "zone": "Delhi", "skills": ["construction", "civil engineering", "disaster relief"], "status": "available", "impact_points": 410, "impact_stats": {"total_tasks_completed": 16, "total_people_helped": 290}, "max_distance_km": 20},
            {"display_name": "Neha Saxena", "email": "neha.s@example.com", "lat": 28.6100, "lng": 77.2300, "zone": "Delhi", "skills": ["medical doctor", "patient care", "hindi speaking"], "status": "available", "impact_points": 630, "impact_stats": {"total_tasks_completed": 25, "total_people_helped": 420}, "max_distance_km": 15},
        ]

        for i, v in enumerate(volunteers):
            self.add("volunteers", v, doc_id=f"v{i+1}")

        # ── Seed Need Reports ────────────────────────────────
        needs = [
            {"zone": "Dharavi", "lat": 19.0441, "lng": 72.8557, "issue_type": "food", "severity_score": 9, "urgency_score": 95, "urgency_label": "critical", "affected_count": 200, "summary": "Severe food shortage affecting over 200 families.", "required_skills": ["food distribution", "hindi speaking"], "recommended_volunteer_count": 5, "status": "open", "source": "photo", "report_frequency_30d": 8, "trend_direction": "rising", "coordinator_explanation": "Severe food crisis in sector 5."},
            {"zone": "Dharavi", "lat": 19.0438, "lng": 72.8560, "issue_type": "water", "severity_score": 8, "urgency_score": 88, "urgency_label": "critical", "affected_count": 150, "summary": "Water supply contaminated in sector 5. Residents with stomach illness.", "required_skills": ["water purification", "plumbing"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 5, "trend_direction": "rising", "coordinator_explanation": "The main water pipeline serving sector 5 has been compromised."},
            {"zone": "Dharavi", "lat": 19.0430, "lng": 72.8550, "issue_type": "health", "severity_score": 9, "urgency_score": 92, "urgency_label": "critical", "affected_count": 175, "summary": "Medical camp urgently needed — increasing dengue cases.", "required_skills": ["medical first aid", "nursing"], "recommended_volunteer_count": 4, "status": "open", "source": "whatsapp", "report_frequency_30d": 6, "trend_direction": "rising"},
            {"zone": "Kurla", "lat": 19.0724, "lng": 72.8787, "issue_type": "health", "severity_score": 7, "urgency_score": 72, "urgency_label": "high", "affected_count": 80, "summary": "Healthcare facility severely understaffed.", "required_skills": ["medical doctor", "patient care"], "recommended_volunteer_count": 2, "status": "open", "source": "csv", "report_frequency_30d": 3, "trend_direction": "stable"},
            {"zone": "Govandi", "lat": 19.0565, "lng": 72.9230, "issue_type": "housing", "severity_score": 8, "urgency_score": 82, "urgency_label": "high", "affected_count": 120, "summary": "Flooding has damaged 120 homes, families displaced.", "required_skills": ["construction", "disaster relief"], "recommended_volunteer_count": 6, "status": "open", "source": "manual", "report_frequency_30d": 4, "trend_direction": "rising"},
            {"zone": "Bandra East", "lat": 19.0596, "lng": 72.8403, "issue_type": "education", "severity_score": 5, "urgency_score": 48, "urgency_label": "medium", "affected_count": 60, "summary": "Community school needs tutors for exam preparation.", "required_skills": ["teaching", "counseling"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Andheri East", "lat": 19.1197, "lng": 72.8755, "issue_type": "food", "severity_score": 6, "urgency_score": 65, "urgency_label": "high", "affected_count": 90, "summary": "Ration shop closed for 2 weeks, families running low on supplies.", "required_skills": ["food distribution", "logistics"], "recommended_volunteer_count": 3, "status": "open", "source": "whatsapp", "report_frequency_30d": 3, "trend_direction": "stable"},
            {"zone": "Worli", "lat": 19.0144, "lng": 72.8133, "issue_type": "safety", "severity_score": 7, "urgency_score": 70, "urgency_label": "high", "affected_count": 45, "summary": "Building structural damage — residents need safety assessment.", "required_skills": ["civil engineering", "structural assessment"], "recommended_volunteer_count": 2, "status": "open", "source": "manual", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Malad East", "lat": 19.1864, "lng": 72.8356, "issue_type": "water", "severity_score": 6, "urgency_score": 55, "urgency_label": "medium", "affected_count": 70, "summary": "Water tanker delivery delayed by 3 days.", "required_skills": ["logistics", "driving"], "recommended_volunteer_count": 2, "status": "open", "source": "csv", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Chembur", "lat": 19.0625, "lng": 72.8956, "issue_type": "health", "severity_score": 6, "urgency_score": 58, "urgency_label": "medium", "affected_count": 55, "summary": "Need for basic health check-up camp in slum area.", "required_skills": ["medical first aid", "pharmacy"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 1, "trend_direction": "stable"},
            {"zone": "Dharavi", "lat": 19.0435, "lng": 72.8545, "issue_type": "food", "severity_score": 7, "urgency_score": 78, "urgency_label": "high", "affected_count": 100, "summary": "Community kitchen shut down, 100+ families without meals.", "required_skills": ["cooking", "food distribution"], "recommended_volunteer_count": 4, "status": "assigned", "source": "photo", "report_frequency_30d": 5, "trend_direction": "rising"},
            {"zone": "Kurla", "lat": 19.0710, "lng": 72.8800, "issue_type": "water", "severity_score": 5, "urgency_score": 42, "urgency_label": "medium", "affected_count": 35, "summary": "Broken water pipe needs repair in residential block.", "required_skills": ["plumbing"], "recommended_volunteer_count": 1, "status": "resolved", "source": "manual", "report_frequency_30d": 1, "trend_direction": "stable"},
        ]

        for i, n in enumerate(needs):
            self.add("need_reports", n, doc_id=f"n{i+1}")

        # ── Seed Users ───────────────────────────────────────
        users = [
            {"email": "admin@allocare.org", "password_hash": self.hash_password("admin123"), "display_name": "Demo Organization", "role": "organization"},
            {"email": "volunteer@allocare.org", "password_hash": self.hash_password("vol123"), "display_name": "Demo Volunteer", "role": "volunteer"},
        ]
        for i, u in enumerate(users):
            self.add("users", u, doc_id=f"u{i+1}")

        logger.info(f"[DataStore-Local] Seeded {len(needs)} needs + {len(volunteers)} volunteers + {len(users)} users")


# ── Global singleton ─────────────────────────────────────────
store = DataStore()
