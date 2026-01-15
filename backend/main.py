import os
import uvicorn
import datetime
from fastapi import FastAPI, BackgroundTasks, Request
from google.cloud import firestore

app = FastAPI()

from pydantic import BaseModel
from typing import Optional

# ... previous imports ...
# ... app init ...

# Pydantic Model for Log Entry
class LogEntry(BaseModel):
    method: str
    path: str
    status_code: int
    process_time_seconds: float
    client_ip: str
    timestamp: Optional[str] = None # Filled by server or converted string

# Initialize Firestore Client
db = firestore.Client()
LOG_COLLECTION = "api_logs"

def save_log_to_firestore(log_entry: LogEntry):
    """Writes the log entry to Firestore (background)."""
    try:
        data = log_entry.dict()
        # Use server timestamp for accuracy
        data["timestamp"] = firestore.SERVER_TIMESTAMP
        db.collection(LOG_COLLECTION).add(data)
        print(f"Log saved: {log_entry.path}")
    except Exception as e:
        print(f"Failed to save log: {e}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to capture request and response details.
    Runs logging as a background task to avoid blocking the response.
    """
    # 1. Capture Request Details
    method = request.method
    path = request.url.path
    
    # Ignore health checks to prevent log spam
    if path == "/health":
        return await call_next(request)

    # 2. Process Request
    start_time = datetime.datetime.now()
    response = await call_next(request)
    process_time = (datetime.datetime.now() - start_time).total_seconds()

    # 3. Prepare Log Data
    try:
        log_model = LogEntry(
            method=method,
            path=path,
            status_code=response.status_code,
            process_time_seconds=process_time,
            client_ip=request.client.host if request.client else "unknown"
        )
        save_log_to_firestore(log_model)
    except Exception as validation_err:
        print(f"Log validation failed: {validation_err}")

    return response

@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "Cloud Run with Terraform"}

@app.get("/hello/{name}")
def read_item(name: str):
    return {"message": f"Hello {name}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/logs")
def get_recent_logs(limit: int = 50):
    """Retrieve the latest API logs from Firestore."""
    try:
        docs = (
            db.collection(LOG_COLLECTION)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        
        logs = []
        for doc in docs:
            data = doc.to_dict()
            # Convert timestamp to string for JSON serialization
            if "timestamp" in data and data["timestamp"]:
                data["timestamp"] = data["timestamp"].isoformat()
            logs.append(data)
            
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        return {"error": str(e)}

@app.get("/secret")
def read_secret():
    secret_value = os.environ.get("SECRET_KEY", "not_found")
    # Return masked value for security demo
    masked = secret_value[:2] + "****" if secret_value != "not_found" else "not_found"
    return {"secret_key_status": "loaded", "value": masked}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
