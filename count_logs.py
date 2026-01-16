from google.cloud import firestore
import os

# Set project
os.environ["GOOGLE_CLOUD_PROJECT"] = "cloudrunantigravity"

db = firestore.Client(database="(default)")

# Count logs
logs_ref = db.collection("api_logs")
docs = list(logs_ref.stream())
print(f"📊 Total Logs in Firestore: {len(docs)}")
