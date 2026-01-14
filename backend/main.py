import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/hello/{name}")
def read_item(name: str):
    return {"message": f"Hello {name}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/secret")
def read_secret():
    secret_value = os.environ.get("SECRET_KEY", "not_found")
    # Return masked value for security demo
    masked = secret_value[:2] + "****" if secret_value != "not_found" else "not_found"
    return {"secret_key_status": "loaded", "value": masked}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
