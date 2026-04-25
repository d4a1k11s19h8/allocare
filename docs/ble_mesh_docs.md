# AlloCare: BLE Mesh & Offline Communication Architecture

## Overview

AlloCare supports three offline communication channels for areas with no internet:

1. **Service Worker + PWA** (implemented): Offline dashboard access and queued submissions
2. **SMS Gateway** (implemented): Text-based report submission via `POST /api/sms/receive`
3. **BLE Mesh Network** (architecture spec below): Device-to-device data sync

---

## SMS Gateway Usage

### Sending a Report via SMS
Format: `NEED <location> <issue_type> <description>`

Examples:
```
NEED Dharavi food 200 families without meals for 3 days
NEED Delhi health Dengue outbreak 50 cases reported in sector 7
NEED Kolkata water Pipeline broken, 100 households affected
```

### API Endpoint
```
POST /api/sms/receive
Body: { "sender": "+91XXXXXXXXXX", "message": "NEED Delhi food ..." }
```

For production, integrate with:
- **Twilio** (trial available): Webhook forwards SMS to this endpoint
- **Exotel** (India-focused): Indian number support
- **TextLocal**: Bulk SMS for volunteer notifications

---

## BLE Mesh Network Architecture

### Purpose
Enable volunteers in disaster zones (no cell/internet) to:
- Share need reports between nearby devices
- Propagate urgency updates across a mesh
- Coordinate assignments without a central server

### Protocol Design

#### BLE Advertising Packet Structure
```
┌─────────────┬──────────┬───────────┬──────────┬────────────┐
│ Header (2B) │ Type(1B) │ Zone(8B)  │Score(1B) │ Payload    │
│  0xAC 0x01  │          │           │          │ (up to 20B)│
├─────────────┼──────────┼───────────┼──────────┼────────────┤
│ Magic bytes │ 0x01=Need│ UTF-8     │ 0-100    │ Summary    │
│             │ 0x02=Vol │ truncated │ urgency  │ truncated  │
│             │ 0x03=Ack │           │          │            │
└─────────────┴──────────┴───────────┴──────────┴────────────┘
```

#### Message Types
| Type | Name | Description |
|------|------|-------------|
| 0x01 | NEED_REPORT | New community need (location + issue + severity) |
| 0x02 | VOL_STATUS | Volunteer availability beacon |
| 0x03 | ASSIGNMENT_ACK | Volunteer accepted an assignment |
| 0x04 | SYNC_REQUEST | Request full data sync via GATT |

#### Mesh Propagation Rules
1. Each device re-broadcasts received packets with TTL decremented
2. Maximum TTL = 5 hops (prevents infinite propagation)
3. Seen packet IDs cached for 10 minutes (prevents loops)
4. Priority: NEED_REPORT packets get higher advertising frequency

### Implementation Path

#### Phase 1: Web Bluetooth (Chrome)
- Use Web Bluetooth API for direct device pairing
- Limited to 1:1 connections, no mesh
- Good for: coordinator ↔ volunteer data transfer

```javascript
// Example: Web Bluetooth scan for AlloCare devices
navigator.bluetooth.requestDevice({
  filters: [{ namePrefix: 'AC-' }],
  optionalServices: ['allocare-sync']
});
```

#### Phase 2: React Native / Flutter Companion App
- Full BLE peripheral + central mode
- Background BLE advertising
- True mesh topology with multi-hop relay
- Recommended libraries:
  - **react-native-ble-plx** (React Native)
  - **flutter_blue_plus** (Flutter)
  - **Android BLE API** (native, best performance)

#### Phase 3: LoRa Integration (Rural Areas)
- For areas beyond BLE range (>100m)
- LoRa modules (SX1276) connected to Raspberry Pi gateways
- 2-5km range with low power consumption
- Bridge: LoRa gateway ↔ local WiFi ↔ AlloCare API

### Data Sync Protocol (GATT Service)
```
Service UUID: 0000AC00-0000-1000-8000-00805F9B34FB
  Characteristic: NeedReports  (0000AC01-...): READ/NOTIFY
  Characteristic: VolunteerStatus (0000AC02-...): READ/NOTIFY  
  Characteristic: SyncControl (0000AC03-...): WRITE
```

---

## Current Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| Service Worker (PWA) | ✅ Done | `public/sw.js` |
| IndexedDB offline cache | ✅ Done | `public/js/offline.js` |
| Offline report queue | ✅ Done | `public/js/offline.js` |
| Network status indicator | ✅ Done | `index.html` + `offline.js` |
| SMS Gateway endpoint | ✅ Done | `main.py: /api/sms/receive` |
| BLE Mesh Protocol | 📋 Spec | This document |
| Companion App | 🔮 Future | Requires React Native/Flutter |
| LoRa Gateway | 🔮 Future | Requires hardware |
