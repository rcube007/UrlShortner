# main.py
from fastapi import FastAPI, Request, HTTPException, Depends
from sqlalchemy.orm import Session

try:
    from .db import SessionLocal, URL, IdempotencyKey, Base
except ImportError:
    from db import SessionLocal, URL, IdempotencyKey, Base

import hashlib, uuid, redis, datetime
from redis.exceptions import ConnectionError

app = FastAPI()

# Redis for rate limiting
try:
    r = redis.Redis(host="localhost", port=6379, db=0)
    r.ping()
except ConnectionError:
    r = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Rate limiting middleware
def rate_limit(ip: str, limit: int, window: int = 60):
    if r is None:
        return

    key = f"rate:{ip}"
    try:
        current = r.get(key)
        if current and int(current) >= limit:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        else:
            pipe = r.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, window)
            pipe.execute()
    except ConnectionError:
        return

@app.post("/shorten")
def shorten_url(request: Request, long_url: str, custom_alias: str = None, db: Session = Depends(get_db)):
    ip = request.client.host
    rate_limit(ip, limit=10)  # 10 requests/minute

    # Idempotency key
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
    if existing:
        return {"short_url": existing.response}

    alias = custom_alias or str(uuid.uuid4())[:6]
    new_url = URL(alias=alias, long_url=long_url)
    db.add(new_url)
    db.commit()

    short_url = f"http://localhost:8000/{alias}"

    # Save idempotency record
    record = IdempotencyKey(
        key=idempotency_key,
        request_hash=hashlib.sha256(long_url.encode()).hexdigest(),
        response=short_url
    )
    db.add(record)
    db.commit()

    return {"short_url": short_url, "alias": alias, "long_url": long_url}

@app.get("/{alias}")
def redirect(alias: str, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    rate_limit(ip, limit=100)  # 100 requests/minute

    url = db.query(URL).filter(URL.alias == alias).first()
    if not url:
        raise HTTPException(status_code=404, detail="Alias not found")

    url.clicks += 1
    db.commit()
    return {"redirect_to": url.long_url}

@app.get("/info/{alias}")
def info(alias: str, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    rate_limit(ip, limit=50)  # 50 requests/minute

    url = db.query(URL).filter(URL.alias == alias).first()
    if not url:
        raise HTTPException(status_code=404, detail="Alias not found")

    return {
        "alias": url.alias,
        "long_url": url.long_url,
        "created_at": url.created_at,
        "clicks": url.clicks
    }

@app.delete("/delete/{alias}")
def delete(alias: str, db: Session = Depends(get_db)):
    url = db.query(URL).filter(URL.alias == alias).first()
    if not url:
        return {"message": "Already deleted or not found"}
    db.delete(url)
    db.commit()
    return {"message": "Short URL deleted successfully", "alias": alias}
