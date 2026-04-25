import json
import os
import sys
from firebase_admin import initialize_app, credentials, firestore

def run():
    creds_json = os.environ.get("FIREBASE_CREDENTIALS")
    if not creds_json:
        print("Please set the FIREBASE_CREDENTIALS environment variable.")
        sys.exit(1)

    print("Initializing Firebase...")
    creds_dict = json.loads(creds_json)
    cred = credentials.Certificate(creds_dict)
    initialize_app(cred)

    db = firestore.client()
    
    if not os.path.exists("backend/data.json"):
        print("backend/data.json not found! Nothing to migrate.")
        sys.exit(0)

    print("Reading local data.json...")
    with open("backend/data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for collection, docs in data.items():
        print(f"\nMigrating collection: {collection}...")
        for doc_id, doc_data in docs.items():
            db.collection(collection).document(doc_id).set(doc_data)
            print(f"  -> Uploaded {doc_id}")

    print("\n✅ Migration complete! Your local accounts are now permanently in Firestore.")

if __name__ == "__main__":
    run()
