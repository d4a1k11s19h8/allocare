"""
data_store.py — Thread-safe in-memory data store replacing Firestore.
Persists to data.json for durability across restarts.
"""
import os
import json
import uuid
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"


class DataStore:
    """Simple in-memory document store with JSON persistence."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, dict]] = {
            "need_reports": {},
            "volunteers": {},
            "assignments": {},
            "urgency_corrections": {},
            "zone_stats": {},
            "organizations": {},
        }
        self._load()

    # ── Persistence ────────────────────────────────────────────
    def _load(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for col in self._data:
                        if col in loaded:
                            self._data[col] = loaded[col]
                logger.info(f"[DataStore] Loaded {sum(len(v) for v in self._data.values())} docs from {DATA_FILE}")
            except Exception as e:
                logger.warning(f"[DataStore] Could not load {DATA_FILE}: {e}")

    def _save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[DataStore] Save error: {e}")

    # ── CRUD Operations ────────────────────────────────────────
    def add(self, collection: str, data: dict, doc_id: str = None) -> str:
        with self._lock:
            doc_id = doc_id or str(uuid.uuid4())[:20]
            data["_id"] = doc_id
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc).isoformat()
            self._data.setdefault(collection, {})[doc_id] = data
            self._save()
            return doc_id

    def get(self, collection: str, doc_id: str) -> Optional[dict]:
        with self._lock:
            doc = self._data.get(collection, {}).get(doc_id)
            return dict(doc) if doc else None

    def update(self, collection: str, doc_id: str, updates: dict) -> bool:
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id not in col:
                return False
            col[doc_id].update(updates)
            col[doc_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return True

    def delete(self, collection: str, doc_id: str) -> bool:
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id in col:
                del col[doc_id]
                self._save()
                return True
            return False

    def list_all(self, collection: str) -> List[dict]:
        with self._lock:
            return [dict(doc) for doc in self._data.get(collection, {}).values()]

    def query(
        self,
        collection: str,
        filters: Dict[str, Any] = None,
        order_by: str = None,
        descending: bool = False,
        limit: int = 100,
    ) -> List[dict]:
        with self._lock:
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
            if doc_id not in col:
                return False
            current = col[doc_id].get(field, 0)
            if isinstance(current, (int, float)):
                col[doc_id][field] = current + amount
            else:
                col[doc_id][field] = amount
            self._save()
            return True

    def set_nested(self, collection: str, doc_id: str, path: str, value: Any) -> bool:
        """Set a nested field like 'impact_stats.total_tasks_completed'."""
        with self._lock:
            col = self._data.get(collection, {})
            if doc_id not in col:
                return False
            parts = path.split(".")
            obj = col[doc_id]
            for p in parts[:-1]:
                if p not in obj or not isinstance(obj[p], dict):
                    obj[p] = {}
                obj = obj[p]
            current = obj.get(parts[-1], 0)
            if isinstance(value, (int, float)) and isinstance(current, (int, float)):
                obj[parts[-1]] = current + value
            else:
                obj[parts[-1]] = value
            self._save()
            return True

    def clear_collection(self, collection: str):
        with self._lock:
            self._data[collection] = {}
            self._save()

    def seed_demo_data(self):
        """Load seed data if collections are empty."""
        if self._data.get("need_reports") and len(self._data["need_reports"]) > 0:
            logger.info("[DataStore] Data already exists, skipping seed.")
            return

        logger.info("[DataStore] Seeding demo data...")

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
        ]

        for i, v in enumerate(volunteers):
            self.add("volunteers", v, doc_id=f"v{i+1}")

        # ── Seed Need Reports ────────────────────────────────
        needs = [
            {"zone": "Dharavi", "lat": 19.0441, "lng": 72.8557, "issue_type": "food", "severity_score": 9, "urgency_score": 95, "urgency_label": "critical", "affected_count": 200, "summary": "Severe food shortage affecting over 200 families. Children and elderly most affected.", "required_skills": ["food distribution", "hindi speaking"], "recommended_volunteer_count": 5, "status": "open", "source": "photo", "report_frequency_30d": 8, "trend_direction": "rising", "coordinator_explanation": "In Dharavi's sector 5, a severe food crisis is unfolding. Over 200 families, including many with young children and elderly members, have reported running out of food supplies. The community's usual distribution networks have broken down due to access road flooding. This needs immediate attention as children have reportedly gone without meals for over 48 hours."},
            {"zone": "Dharavi", "lat": 19.0438, "lng": 72.8560, "issue_type": "water", "severity_score": 8, "urgency_score": 88, "urgency_label": "critical", "affected_count": 150, "summary": "Water supply contaminated in sector 5. Residents with stomach illness.", "required_skills": ["water purification", "plumbing"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 5, "trend_direction": "rising", "coordinator_explanation": "The main water pipeline serving sector 5 has been compromised, likely due to sewage infiltration. At least 150 residents are affected and several have reported gastrointestinal symptoms. The local municipal office has been notified but response time is typically 3-5 days. We need volunteer plumbers on-site immediately."},
            {"zone": "Dharavi", "lat": 19.0430, "lng": 72.8550, "issue_type": "health", "severity_score": 9, "urgency_score": 92, "urgency_label": "critical", "affected_count": 175, "summary": "Medical camp urgently needed — increasing dengue cases. 3 children hospitalized.", "required_skills": ["medical first aid", "nursing"], "recommended_volunteer_count": 4, "status": "open", "source": "whatsapp", "report_frequency_30d": 6, "trend_direction": "rising"},
            {"zone": "Kurla", "lat": 19.0724, "lng": 72.8787, "issue_type": "health", "severity_score": 7, "urgency_score": 72, "urgency_label": "high", "affected_count": 80, "summary": "Healthcare facility severely understaffed. Patients waiting 6+ hours.", "required_skills": ["medical doctor", "patient care"], "recommended_volunteer_count": 2, "status": "open", "source": "csv", "report_frequency_30d": 3, "trend_direction": "stable"},
            {"zone": "Govandi", "lat": 19.0537, "lng": 72.9148, "issue_type": "housing", "severity_score": 8, "urgency_score": 85, "urgency_label": "high", "affected_count": 60, "summary": "Multiple families in structurally damaged housing. Monsoon risk.", "required_skills": ["construction", "civil engineering"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 4, "trend_direction": "rising"},
            {"zone": "Malad", "lat": 19.1860, "lng": 72.8485, "issue_type": "education", "severity_score": 6, "urgency_score": 62, "urgency_label": "high", "affected_count": 120, "summary": "School closed due to structural issues. 120 students need temporary facility.", "required_skills": ["teaching", "event coordination"], "recommended_volunteer_count": 3, "status": "open", "source": "csv", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Bandra East", "lat": 19.0596, "lng": 72.8413, "issue_type": "safety", "severity_score": 5, "urgency_score": 42, "urgency_label": "medium", "affected_count": 300, "summary": "Broken street lights creating dangerous conditions at night.", "required_skills": ["electrical"], "recommended_volunteer_count": 2, "status": "open", "source": "manual", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Kurla", "lat": 19.0740, "lng": 72.8800, "issue_type": "water", "severity_score": 8, "urgency_score": 90, "urgency_label": "critical", "affected_count": 200, "summary": "Clean drinking water crisis. Municipal water tanker absent 5 days.", "required_skills": ["water purification", "logistics"], "recommended_volunteer_count": 3, "status": "open", "source": "photo", "report_frequency_30d": 7, "trend_direction": "rising"},
            {"zone": "Andheri West", "lat": 19.1360, "lng": 72.8264, "issue_type": "health", "severity_score": 8, "urgency_score": 82, "urgency_label": "high", "affected_count": 200, "summary": "Community health clinic lost its doctor. 200 patients/week without medical access.", "required_skills": ["medical doctor", "nursing"], "recommended_volunteer_count": 2, "status": "open", "source": "manual", "report_frequency_30d": 4, "trend_direction": "rising"},
            {"zone": "Sion", "lat": 19.0404, "lng": 72.8620, "issue_type": "food", "severity_score": 8, "urgency_score": 87, "urgency_label": "critical", "affected_count": 100, "summary": "Food bank running low — only 3 days of supply remaining. Serves 100 families daily.", "required_skills": ["food distribution", "cooking"], "recommended_volunteer_count": 4, "status": "open", "source": "csv", "report_frequency_30d": 5, "trend_direction": "rising"},
            {"zone": "Vikhroli", "lat": 19.0980, "lng": 72.9167, "issue_type": "water", "severity_score": 8, "urgency_score": 86, "urgency_label": "critical", "affected_count": 350, "summary": "Water pipeline burst — entire neighborhood without water for 3 days.", "required_skills": ["plumbing", "construction"], "recommended_volunteer_count": 4, "status": "open", "source": "whatsapp", "report_frequency_30d": 3, "trend_direction": "rising"},
            {"zone": "Worli", "lat": 19.0088, "lng": 72.8170, "issue_type": "housing", "severity_score": 8, "urgency_score": 78, "urgency_label": "high", "affected_count": 60, "summary": "Unsafe building with cracks in walls. 12 families at risk.", "required_skills": ["structural assessment", "civil engineering"], "recommended_volunteer_count": 2, "status": "open", "source": "manual", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Kurla West", "lat": 19.0730, "lng": 72.8770, "issue_type": "safety", "severity_score": 9, "urgency_score": 91, "urgency_label": "critical", "affected_count": 15, "summary": "Street children sleeping under bridge near railway station. Need shelter and food.", "required_skills": ["social work", "child care"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 6, "trend_direction": "rising"},
            {"zone": "Mankhurd", "lat": 19.0635, "lng": 72.9277, "issue_type": "education", "severity_score": 5, "urgency_score": 35, "urgency_label": "medium", "affected_count": 45, "summary": "Children not attending school — nearest school is 4km away. Need transport.", "required_skills": ["driving", "teaching"], "recommended_volunteer_count": 2, "status": "open", "source": "csv", "report_frequency_30d": 1, "trend_direction": "stable"},
            {"zone": "Dharavi", "lat": 19.0445, "lng": 72.8540, "issue_type": "housing", "severity_score": 9, "urgency_score": 93, "urgency_label": "critical", "affected_count": 40, "summary": "8 families displaced after fire in 13th compound. Currently sleeping on streets.", "required_skills": ["construction", "carpentry", "logistics"], "recommended_volunteer_count": 5, "status": "open", "source": "photo", "report_frequency_30d": 9, "trend_direction": "rising"},
            {"zone": "Kandivali", "lat": 19.2045, "lng": 72.8403, "issue_type": "food", "severity_score": 7, "urgency_score": 68, "urgency_label": "high", "affected_count": 150, "summary": "Community kitchen running out of funds. Feeds 150 people daily.", "required_skills": ["cooking", "food distribution", "event coordination"], "recommended_volunteer_count": 3, "status": "open", "source": "manual", "report_frequency_30d": 3, "trend_direction": "stable"},
            {"zone": "Dharavi", "lat": 19.0446, "lng": 72.8541, "issue_type": "safety", "severity_score": 9, "urgency_score": 94, "urgency_label": "critical", "affected_count": 8, "summary": "Child labor reported in leather workshop. 8 children aged 10-14 found working.", "required_skills": ["social work", "legal aid"], "recommended_volunteer_count": 2, "status": "open", "source": "manual", "report_frequency_30d": 4, "trend_direction": "rising"},
            {"zone": "Chembur", "lat": 19.0620, "lng": 72.8978, "issue_type": "health", "severity_score": 8, "urgency_score": 75, "urgency_label": "high", "affected_count": 25, "summary": "Elderly in Old Age Home running out of medications. Diabetes and BP medicines finished.", "required_skills": ["pharmacy", "medical first aid"], "recommended_volunteer_count": 1, "status": "open", "source": "csv", "report_frequency_30d": 2, "trend_direction": "stable"},
            {"zone": "Dharavi", "lat": 19.0435, "lng": 72.8545, "issue_type": "education", "severity_score": 4, "urgency_score": 22, "urgency_label": "low", "affected_count": 60, "summary": "Educational materials needed for community learning center. 60 students need textbooks.", "required_skills": ["teaching"], "recommended_volunteer_count": 1, "status": "open", "source": "csv", "report_frequency_30d": 1, "trend_direction": "stable"},
            {"zone": "Jogeshwari", "lat": 19.1371, "lng": 72.8570, "issue_type": "safety", "severity_score": 7, "urgency_score": 65, "urgency_label": "high", "affected_count": 100, "summary": "Women's safety patrol needed — multiple eve-teasing incidents near public toilet.", "required_skills": ["women safety", "social work"], "recommended_volunteer_count": 3, "status": "open", "source": "whatsapp", "report_frequency_30d": 3, "trend_direction": "rising"},
        ]

        for i, n in enumerate(needs):
            self.add("need_reports", n, doc_id=f"n{i+1}")

        logger.info(f"[DataStore] Seeded {len(needs)} needs + {len(volunteers)} volunteers")


# ── Global singleton ─────────────────────────────────────────
store = DataStore()
