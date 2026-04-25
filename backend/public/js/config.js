/* ═══════════════════════════════════════════════════════════
   AlloCare: Configuration
   No Firebase, no paid APIs. Pure local backend.
   ═════════════════════════════════════════════════════════ */

// Backend API URL
const FUNCTIONS_BASE = window.location.hostname === "localhost" 
  ? "http://localhost:8000" 
  : window.location.origin;

// App State
const AppState = {
  user: null,
  orgId: "demo_org",
  needs: [],
  volunteers: [],
  selectedNeedId: null,
  map: null,
  markers: [],
  heatmapData: [],
  filters: {
    type: "all",
    urgency: "all",
    search: "",
  },
};

// Issue type config
const ISSUE_TYPES = {
  food: { icon: "🍚", label: "Food", color: "#F97316" },
  water: { icon: "💧", label: "Water", color: "#3B82F6" },
  health: { icon: "🏥", label: "Health", color: "#EF4444" },
  housing: { icon: "🏠", label: "Housing", color: "#8B5CF6" },
  education: { icon: "📚", label: "Education", color: "#06B6D4" },
  safety: { icon: "🛡️", label: "Safety", color: "#F59E0B" },
  other: { icon: "📋", label: "Other", color: "#6B7280" },
};

// Urgency config
const URGENCY_LEVELS = {
  critical: { label: "CRITICAL", color: "#E02424", min: 86 },
  high: { label: "HIGH", color: "#F97316", min: 61 },
  medium: { label: "MEDIUM", color: "#E3A008", min: 31 },
  low: { label: "LOW", color: "#0E9F6E", min: 0 },
};

// Avatar colors for volunteers
const AVATAR_COLORS = [
  "#1A56DB", "#7C3AED", "#DB2777", "#DC2626",
  "#EA580C", "#16A34A", "#0891B2", "#9333EA",
];

function getAvatarColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getInitials(name) {
  return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
}

function timeAgo(date) {
  if (!date) return "";
  const d = date instanceof Date ? date : new Date(date);
  const now = new Date();
  const diffMs = now - d;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
