import os
import uvicorn
import datetime
import asyncio
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from google.cloud import firestore
from pydantic import BaseModel
from typing import Optional

# Security Monitoring
from sentinel import (
    check_monitored_path, get_static_response, analyze_request,
    check_user_agent, calculate_threat_level,
    SecurityEvent, ThreatLevel, SensorType
)

# Security Alerting
from alerting import send_security_alert

# Caching Imports
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

app = FastAPI()

# ------------------------------------------------------------------------------
# Redis Cache Initialization (Enterprise Only)
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    redis_host = os.environ.get("REDIS_HOST")
    if redis_host:
        print(f"✅ Enterprise Mode: Connecting to Redis at {redis_host}...")
        try:
            redis = aioredis.from_url(f"redis://{redis_host}", encoding="utf8", decode_responses=True)
            FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
            print("✅ Redis Cache Initialized.")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            # Fallback will happen automatically as decorators won't find backend? 
            # Actually fastapi-cache might fail if not init. 
            # We need to handle this carefully.
    else:
        print("ℹ️ Simple Mode: Running without Redis Cache.")
        # Init with InMemory or Dummy to prevent decorator errors?
        # fast-api cache needs init.
        # We can init an InMemoryBackend for local/simple mode if we want caching,
        # or just not use the decorator if not needed. 
        # But decorators are static.
        # Ideally we use InMemoryBackend for Simple Mode.
        from fastapi_cache.backends.inmemory import InMemoryBackend
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")


# Initialize Firestore Client
# ...

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
EVENT_COLLECTION = "security_events"

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


def save_security_event(event: SecurityEvent):
    """Writes security event to Firestore."""
    try:
        data = event.dict()
        data["timestamp"] = firestore.SERVER_TIMESTAMP
        db.collection(EVENT_COLLECTION).add(data)
        print(f"📋 Event logged: {event.threat_level} - {event.path}")
    except Exception as e:
        print(f"Failed to save event: {e}")


async def delayed_response(delay: int = 5):
    """Delayed response for rate limiting."""
    await asyncio.sleep(delay)
    return PlainTextResponse(
        content="Internal Server Error",
        status_code=500
    )


# ------------------------------------------------------------------------------
# Security Monitoring Middleware
# ------------------------------------------------------------------------------
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Multi-layer security monitoring.
    Validates endpoints, request patterns, and client signatures.
    """
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    query_string = str(request.query_params) if request.query_params else None
    
    indicators = []
    threat_level = ThreatLevel.LOW
    sensor_type = None
    path_category = None
    
    # Layer 1: Monitored Path Detection
    path_category = check_monitored_path(path)
    if path_category:
        indicators.append(f"path:{path_category}")
        threat_level = ThreatLevel.HIGH
        sensor_type = SensorType.ENDPOINT
        
        # Log the security event
        event = SecurityEvent(
            threat_level=threat_level,
            sensor_type=sensor_type,
            triggered_path=path,
            path_category=path_category,
            ip_address=client_ip,
            method=method,
            path=path,
            query_string=query_string,
            user_agent=user_agent,
            headers=dict(request.headers),
            indicators=indicators
        )
        save_security_event(event)
        
        # Send alert (fire and forget)
        asyncio.create_task(send_security_alert(
            threat_level=threat_level.value,
            path=path,
            ip_address=client_ip,
            category=path_category,
            user_agent=user_agent,
            indicators=indicators
        ))
        
        # Check for static response
        static_content = get_static_response(path)
        if static_content:
            await asyncio.sleep(2)
            return PlainTextResponse(content=static_content, media_type="text/plain")
        
        # Default delayed response
        return await delayed_response(delay=5)
    
    # Layer 2: Request Pattern Analysis
    full_url = str(request.url)
    patterns = analyze_request(full_url)
    if patterns:
        indicators.extend([f"sig:{p}" for p in patterns])
        threat_level = ThreatLevel.MEDIUM if len(patterns) == 1 else ThreatLevel.CRITICAL
        sensor_type = SensorType.PATTERN
    
    # Layer 3: Client Signature Check
    if check_user_agent(user_agent):
        indicators.append("scanner_signature")
        if threat_level == ThreatLevel.LOW:
            threat_level = ThreatLevel.LOW
        sensor_type = sensor_type or SensorType.USER_AGENT
    
    # Log if any indicators found
    if indicators and not path_category:
        event = SecurityEvent(
            threat_level=threat_level,
            sensor_type=sensor_type,
            triggered_path=None,
            path_category=None,
            ip_address=client_ip,
            method=method,
            path=path,
            query_string=query_string,
            user_agent=user_agent,
            headers=dict(request.headers),
            indicators=indicators
        )
        save_security_event(event)
    
    # Continue to normal request processing
    return await call_next(request)


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


# ------------------------------------------------------------------------------
# Standard Endpoints
# ------------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "Cloud Run with Terraform"}

@app.get("/hello/{name}")
def read_item(name: str):
    return {"message": f"Hello {name}"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.1", "pipeline": "github-actions"}

@app.get("/logs")
@cache(expire=60)
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
            if "timestamp" in data and data["timestamp"]:
                data["timestamp"] = data["timestamp"].isoformat()
            logs.append(data)
            
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        return {"error": str(e)}

@app.get("/secret")
def read_secret():
    secret_value = os.environ.get("SECRET_KEY", "not_found")
    masked = secret_value[:2] + "****" if secret_value != "not_found" else "not_found"
    return {"secret_key_status": "loaded", "value": masked}


# ------------------------------------------------------------------------------
# Security Event Endpoints
# ------------------------------------------------------------------------------
@app.get("/events")
def get_security_events(limit: int = 50, threat_level: Optional[str] = None):
    """Retrieve security event logs from Firestore."""
    try:
        query = db.collection(EVENT_COLLECTION)
        
        if threat_level:
            query = query.where("threat_level", "==", threat_level)
        
        docs = (
            query
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        
        logs = []
        for doc in docs:
            data = doc.to_dict()
            if "timestamp" in data and data["timestamp"]:
                data["timestamp"] = data["timestamp"].isoformat()
            if "headers" in data:
                data["headers_count"] = len(data["headers"])
                del data["headers"]
            logs.append(data)
            
        return {
            "count": len(logs),
            "events": logs,
            "summary": {
                "high": sum(1 for l in logs if l.get("threat_level") == "high"),
                "medium": sum(1 for l in logs if l.get("threat_level") == "medium"),
                "low": sum(1 for l in logs if l.get("threat_level") == "low"),
                "critical": sum(1 for l in logs if l.get("threat_level") == "critical"),
            }
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/events/stats")
def get_event_stats():
    """Get security event statistics."""
    try:
        docs = db.collection(EVENT_COLLECTION).stream()
        
        stats = {
            "total": 0,
            "by_threat_level": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "by_sensor_type": {},
            "top_paths": {},
            "unique_ips": set()
        }
        
        for doc in docs:
            data = doc.to_dict()
            stats["total"] += 1
            
            level = data.get("threat_level", "low")
            stats["by_threat_level"][level] = stats["by_threat_level"].get(level, 0) + 1
            
            stype = data.get("sensor_type")
            if stype:
                stats["by_sensor_type"][stype] = stats["by_sensor_type"].get(stype, 0) + 1
            
            triggered = data.get("triggered_path")
            if triggered:
                stats["top_paths"][triggered] = stats["top_paths"].get(triggered, 0) + 1
            
            ip = data.get("ip_address")
            if ip:
                stats["unique_ips"].add(ip)
        
        stats["unique_ips"] = len(stats["unique_ips"])
        
        return stats
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

