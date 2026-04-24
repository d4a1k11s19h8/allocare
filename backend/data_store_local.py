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

        # ── Seed Volunteers (Pan-India: 54 volunteers) ──────
        V = lambda n,e,la,ln,z,sk,s,ip,tc,ph,md: {"display_name":n,"email":e,"lat":la,"lng":ln,"zone":z,"skills":sk,"status":s,"impact_points":ip,"impact_stats":{"total_tasks_completed":tc,"total_people_helped":ph},"max_distance_km":md}
        volunteers = [
            # ── WEST: Mumbai ──
            V("Priya Sharma","priya@example.com",19.045,72.857,"Dharavi",["food distribution","medical first aid","hindi speaking"],"available",580,23,456,15),
            V("Rahul Deshmukh","rahul@example.com",19.073,72.879,"Kurla",["construction","plumbing","electrical"],"available",320,12,180,15),
            V("Anita Patel","anita@example.com",19.054,72.915,"Govandi",["teaching","counseling"],"available",680,18,540,20),
            V("Mohammed Shaikh","mohammed@example.com",19.044,72.855,"Dharavi",["cooking","food distribution","driving"],"available",1450,45,1200,15),
            V("Sneha Nair","sneha@example.com",19.120,72.847,"Andheri East",["nursing","medical first aid","patient care"],"available",890,31,620,20),
            V("Vikram Singh","vikram@example.com",19.187,72.849,"Malad East",["construction","carpentry","heavy lifting"],"assigned",210,8,85,15),
            V("Fatima Khan","fatima@example.com",19.059,72.841,"Bandra East",["social work","counseling","legal aid"],"available",420,15,275,15),
            V("Arjun Mehta","arjun@example.com",19.062,72.898,"Chembur",["pharmacy","medical first aid","data entry"],"available",250,10,150,15),
            V("Ravi Kumar","ravi@example.com",19.040,72.862,"Sion",["driving","food distribution","logistics"],"available",1100,35,900,25),
            V("Kavitha Reddy","kavitha@example.com",19.019,72.844,"Dadar",["medical doctor","patient care"],"available",340,8,160,20),
            V("Tushar Patil","tushar@example.com",19.008,72.817,"Worli",["civil engineering","structural assessment"],"available",190,6,120,15),
            V("Hassan Ali","hassan@example.com",19.204,72.840,"Kandivali",["cooking","food distribution","event coordination"],"available",820,28,700,20),
            # ── WEST: Pune ──
            V("Sanjay Kulkarni","sanjay.k@example.com",18.520,73.856,"Pune",["civil engineering","disaster relief","logistics"],"available",550,20,400,30),
            V("Deepa Joshi","deepa.j@example.com",18.530,73.850,"Pune",["nursing","patient care","counseling"],"available",390,14,280,25),
            # ── WEST: Ahmedabad / Surat ──
            V("Kiran Patel","kiran.p@example.com",23.022,72.571,"Ahmedabad",["food distribution","logistics","driving"],"available",470,18,350,30),
            V("Hetal Shah","hetal.s@example.com",21.170,72.831,"Surat",["teaching","social work","event coordination"],"available",310,11,200,25),
            # ── CENTRAL: Nagpur ──
            V("Amit Deshmukh","amit.d@example.com",21.145,79.088,"Nagpur",["construction","heavy lifting","disaster relief"],"available",720,30,500,30),
            V("Sunita Wankhede","sunita.w@example.com",21.152,79.075,"Nagpur",["nursing","medical first aid","patient care"],"available",560,22,380,25),
            V("Rajesh Thakur","rajesh.t@example.com",21.140,79.100,"Nagpur",["driving","logistics","food distribution"],"available",340,14,220,30),
            V("Meena Bhonsle","meena.b@example.com",21.160,79.095,"Nagpur",["social work","counseling","event coordination"],"available",480,19,310,25),
            # ── CENTRAL: Bhopal / Indore / Raipur ──
            V("Pooja Mishra","pooja.m@example.com",23.259,77.412,"Bhopal",["medical doctor","patient care","hindi speaking"],"available",600,24,410,30),
            V("Rahul Jain","rahul.j@example.com",22.719,75.857,"Indore",["construction","plumbing","electrical"],"available",280,10,160,25),
            V("Lakshmi Sahu","lakshmi.s@example.com",21.251,81.629,"Raipur",["food distribution","cooking","logistics"],"available",350,13,230,30),
            # ── NORTH: Delhi / NCR ──
            V("Arun Gupta","arun.g@example.com",28.628,77.217,"Delhi",["construction","civil engineering","disaster relief"],"available",410,16,290,25),
            V("Neha Saxena","neha.s@example.com",28.610,77.230,"Delhi",["medical doctor","patient care","hindi speaking"],"available",630,25,420,25),
            V("Manish Tiwari","manish.t@example.com",28.535,77.391,"Noida",["driving","logistics","food distribution"],"available",290,11,190,30),
            V("Simran Kaur","simran.k@example.com",28.459,77.026,"Gurgaon",["social work","legal aid","counseling"],"available",440,17,300,25),
            # ── NORTH: Lucknow / Jaipur / Chandigarh ──
            V("Akhil Verma","akhil.v@example.com",26.846,80.946,"Lucknow",["food distribution","driving","hindi speaking"],"available",370,14,250,30),
            V("Sunaina Rajput","sunaina.r@example.com",26.912,75.787,"Jaipur",["teaching","counseling","event coordination"],"available",510,19,360,30),
            V("Harpreet Singh","harpreet.s@example.com",30.733,76.779,"Chandigarh",["construction","plumbing","disaster relief"],"available",430,16,310,30),
            V("Deepak Sharma","deepak.s@example.com",30.316,78.032,"Dehradun",["nursing","medical first aid","patient care"],"available",320,12,200,30),
            V("Gurdeep Kaur","gurdeep.k@example.com",31.634,74.872,"Amritsar",["cooking","food distribution","logistics"],"available",280,10,180,30),
            # ── SOUTH: Bangalore ──
            V("Ramesh Gowda","ramesh.g@example.com",12.971,77.594,"Bangalore",["civil engineering","construction","disaster relief"],"available",520,20,380,30),
            V("Lakshmi Iyer","lakshmi.i@example.com",12.960,77.600,"Bangalore",["medical doctor","nursing","patient care"],"available",680,26,480,25),
            V("Naveen Kumar","naveen.k@example.com",12.980,77.580,"Bangalore",["driving","logistics","food distribution"],"available",340,13,240,30),
            # ── SOUTH: Chennai ──
            V("Murugan S","murugan.s@example.com",13.082,80.270,"Chennai",["construction","plumbing","electrical"],"available",450,17,330,30),
            V("Priya Venkat","priya.v@example.com",13.070,80.250,"Chennai",["teaching","counseling","social work"],"available",380,14,270,25),
            # ── SOUTH: Hyderabad ──
            V("Srinivas Reddy","srinivas.r@example.com",17.385,78.486,"Hyderabad",["food distribution","cooking","logistics"],"available",490,18,360,30),
            V("Ayesha Begum","ayesha.b@example.com",17.390,78.490,"Hyderabad",["nursing","medical first aid","patient care"],"available",560,21,400,25),
            # ── SOUTH: Kochi / Coimbatore / Trivandrum ──
            V("Thomas Mathew","thomas.m@example.com",9.931,76.267,"Kochi",["construction","disaster relief","logistics"],"available",410,15,290,30),
            V("Meera Nair","meera.n@example.com",11.016,76.955,"Coimbatore",["medical doctor","patient care"],"available",330,12,220,25),
            V("Anoop Kumar","anoop.k@example.com",8.524,76.936,"Thiruvananthapuram",["social work","legal aid","counseling"],"available",270,9,160,30),
            # ── EAST: Kolkata ──
            V("Sourav Das","sourav.d@example.com",22.572,88.363,"Kolkata",["food distribution","driving","logistics"],"available",540,20,390,30),
            V("Ritika Sen","ritika.s@example.com",22.580,88.370,"Kolkata",["teaching","counseling","social work"],"available",420,16,300,25),
            V("Arijit Banerjee","arijit.b@example.com",22.560,88.350,"Kolkata",["medical first aid","pharmacy","patient care"],"available",360,13,250,25),
            # ── EAST: Patna / Ranchi / Bhubaneswar ──
            V("Rajiv Prasad","rajiv.p@example.com",25.609,85.137,"Patna",["construction","plumbing","disaster relief"],"available",300,11,210,30),
            V("Anjali Kumari","anjali.k@example.com",23.344,85.309,"Ranchi",["nursing","medical first aid","patient care"],"available",350,13,240,30),
            V("Subhash Mohanty","subhash.m@example.com",20.296,85.824,"Bhubaneswar",["food distribution","logistics","driving"],"available",410,15,290,30),
            # ── NORTHEAST: Guwahati ──
            V("Bhaskar Deka","bhaskar.d@example.com",26.144,91.736,"Guwahati",["construction","disaster relief","logistics"],"available",380,14,260,35),
            V("Priyanka Bora","priyanka.b@example.com",26.150,91.740,"Guwahati",["nursing","medical first aid","social work"],"available",290,10,190,30),
            # ── NORTH: Varanasi / Kanpur ──
            V("Om Prakash","om.p@example.com",25.317,82.973,"Varanasi",["food distribution","cooking","hindi speaking"],"available",460,17,340,30),
            V("Alok Mishra","alok.m@example.com",26.449,80.331,"Kanpur",["civil engineering","construction","disaster relief"],"available",310,11,210,30),
            # ── WEST: Jodhpur ──
            V("Mahendra Rathore","mahendra.r@example.com",26.238,73.024,"Jodhpur",["driving","logistics","food distribution"],"available",250,9,170,35),
            # ── SOUTH: Mysore ──
            V("Girish Hegde","girish.h@example.com",12.295,76.639,"Mysuru",["teaching","social work","event coordination"],"available",370,14,260,25),
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
            {"email": "superadmin@allocare.org", "password_hash": self.hash_password("super123"), "display_name": "Super Admin", "role": "superadmin"},
        ]
        for i, u in enumerate(users):
            self.add("users", u, doc_id=f"u{i+1}")

        logger.info(f"[DataStore-Local] Seeded {len(needs)} needs + {len(volunteers)} volunteers + {len(users)} users")


# ── Global singleton ─────────────────────────────────────────
store = DataStore()
