# AlloCare: Complete API & Cloud Run Deployment Guide

This guide provides step-by-step instructions for acquiring all required Google Cloud, Google Maps, and AI Studio APIs, followed by instructions on how to package and deploy our FastAPI backend directly to **Google Cloud Run**.

---

## 🔑 Part 1: Obtaining the Required API Keys

AlloCare relies on an ecosystem of Google technologies. You will need to obtain API keys from **three** distinct portals:

### A. Google Cloud Platform (Core Compute & Machine Learning)
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new Google Cloud Project (e.g., `allocare-prod`).
3. Ensure that **Billing is enabled** for this project (Cloud Vision and Cloud Run require a billing account, though the free tier covers initial usage).
4. Go to **APIs & Services > Library** and enable the following APIs:
    *   **Cloud Vision API** (For OCR on paper surveys)
    *   **Cloud Translation API** (For multi-language support)
    *   **Cloud Run Admin API** (For deploying the container)
    *   **Cloud Build API** (For building the Docker container)
5. Generally, when running inside Google Cloud Run, your application will use the **Default Compute Service Account**. Ensure this service account has the following IAM Roles:
    *   `roles/datastore.user` (to read/write to Firestore)
    *   `roles/cloudtranslate.user` (to call Translate API)
    *   `roles/cloudvision.developer` (to call Vision API)

### B. Google Maps Platform (Heatmap & Routing)
1. Go to the [Google Maps Platform Console](https://console.cloud.google.com/google/maps-apis/overview).
2. Ensure you have the same `allocare-prod` project selected.
3. Navigate to **APIs** and enable the following:
    *   **Maps JavaScript API** (For rendering the frontend heatmap)
    *   **Geocoding API** (For converting unstructured address text into Latitude/Longitude)
    *   **Distance Matrix API** (For algorithmic volunteer matching based on proximity)
4. Go to **Credentials**, click **Create Credentials > API Key**.
5. **CRITICAL SECURITY STEP:** 
    *   Copy this key. In our backend `.env` file, it will be `MAPS_API_KEY`.
    *   In the Maps console, click your new key and apply **API restrictions** to limit it strictly to the three APIs enabled above. 

### C. Google AI Studio (Gemini 2.0 Brain)
1. Navigate to [Google AI Studio](https://aistudio.google.com/).
2. Click **Get API Key** in the left sidebar.
3. Click **Create API Key**. You can optionally attach it to your existing `allocare-prod` Google Cloud project.
4. Copy this key. In our backend `.env` file, it will be `GEMINI_API_KEY`.

---

## 🛠️ Part 2: Configuring the Application

1. Open `allocare/backend/.env` (or create it from the `.env.example` template) and populate your keys:
   ```env
   # allocare/backend/.env
   GEMINI_API_KEY="AIzaSy...your_gemini_key"
   MAPS_API_KEY="AIzaSy...your_maps_key"
   ```

2. Open `allocare/public/js/config.js` and input your Maps Javascript key for the frontend maps visualization. Also replace `FUNCTIONS_BASE` with the Cloud Run URL after deployment.
   ```javascript
   // allocare/public/js/config.js
   const MAPS_API_KEY = "AIzaSy...your_maps_key";
   ```

3. Initialize your Firebase project to get your frontend connecting to a real Firestore database:
    * Go to the [Firebase Console](https://console.firebase.google.com/).
    * Create a Web App and copy the `firebaseConfig` object into `allocare/public/js/config.js`.
    * Provision a Cloud Firestore database in `asia-south1` (or your preferred region).

---

## 🐳 Part 3: Deploying to Google Cloud Run

We have migrated the original Firebase Functions backend into a robust, high-performance **FastAPI** application bundled with a Dockerfile.

### Prerequisites:
- The [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and initialized.
- Run `gcloud auth login` and `gcloud config set project allocare-prod`.

### Deployment Steps:

**1. Navigate to the backend directory:**
```bash
cd allocare/backend
```

**2. Submit the Docker build to Google Cloud Build:**
We will securely build the container in the cloud and push it to Google Artifact Registry. First, create a repository if you don't have one:
```bash
gcloud artifacts repositories create allocare-repo --repository-format=docker --location=asia-south1
```
Build the container:
```bash
gcloud builds submit --tag asia-south1-docker.pkg.dev/allocare-prod/allocare-repo/allocare-backend
```

**3. Deploy the container to Cloud Run:**
Run the deployment command, passing in your environment variables.
```bash
gcloud run deploy allocare-backend \
  --image asia-south1-docker.pkg.dev/allocare-prod/allocare-repo/allocare-backend \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="YOUR_GEMINI_KEY",MAPS_API_KEY="YOUR_MAPS_KEY"
```

**4. Update your Frontend configuration:**
Upon successful deployment, `gcloud` will output a **Service URL** (e.g., `https://allocare-backend-xxxxxx-em.a.run.app`). 
Copy this URL and paste it into `allocare/public/js/config.js`:
```javascript
const FUNCTIONS_BASE = "https://allocare-backend-xxxxxx-em.a.run.app";
```

## 🎉 Verification

1. To test the backend is alive, navigate to the Service URL provided by Cloud Run. Because we are using FastAPI, simply appending `/docs` will immediately display our interactive API Swagger interface!
   ```text
   https://allocare-backend-xxxxxx-em.a.run.app/docs
   ```
2. Open your local `localhost:3000` (from `npx serve public`), and verify that clicking **Find Volunteers** now actively queries your new Cloud Run service!
