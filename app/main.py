from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from typing import Optional
import os

# Initialize FastAPI app
app = FastAPI(title="Redis Web Service")

# Export app variable explicitly for Uvicorn
__all__ = ["app"]

# Connect to Redis
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", 6379)
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Define data model
class Item(BaseModel):
    key: str
    value: str

@app.get("/")
def read_root():
    return {"message": "FastAPI with Redis web service is running!"}

@app.get("/data/{key}")
def get_item(key: str):
    value = redis_client.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": value}

@app.post("/data", status_code=201)
def create_item(item: Item):
    try:
        redis_client.set(item.key, item.value)
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/{key}")
def delete_item(key: str):
    result = redis_client.delete(key)
    if result == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key deleted successfully"}

# Health check endpoint
@app.get("/health")
def health_check():
    try:
        # Check if Redis is responding
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}