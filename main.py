# main.py
from typing import Optional
import hashlib
import re
import uuid
from urllib.parse import urlparse

import redis
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from redis.exceptions import ConnectionError
from sqlalchemy.orm import Session

try:
    from .db import IdempotencyKey, SessionLocal, URL
except ImportError:
    from db import IdempotencyKey, SessionLocal, URL

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


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_valid_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,32}", alias))


def generate_alias(db: Session, length: int = 6) -> str:
    while True:
        alias = uuid.uuid4().hex[:length]
        if not db.query(URL).filter(URL.alias == alias).first():
            return alias


def rate_limit(ip: str, limit: int, window: int = 60):
    if r is None:
        return

    key = f"rate:{ip}"
    try:
        current = r.get(key)
        if current and int(current) >= limit:
            raise HTTPException(status_code=429, detail="Too Many Requests")

        pipe = r.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, window)
        pipe.execute()
    except ConnectionError:
        return


@app.post("/shorten", status_code=status.HTTP_201_CREATED)
def shorten_url(
    request: Request,
    long_url: str,
    custom_alias: Optional[str] = None,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    rate_limit(ip, limit=10)

    if not long_url or not long_url.strip():
        raise HTTPException(status_code=400, detail="long_url is required")

    if not is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    if custom_alias is not None and not is_valid_alias(custom_alias):
        raise HTTPException(status_code=400, detail="Invalid custom alias")

    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    existing_request = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == idempotency_key)
        .first()
    )
    if existing_request:
        return {"short_url": existing_request.response}

    alias = custom_alias or generate_alias(db)
    existing_alias = db.query(URL).filter(URL.alias == alias).first()
    if existing_alias and custom_alias:
        raise HTTPException(status_code=409, detail="Alias already exists")

    new_url = URL(alias=alias, long_url=long_url)
    db.add(new_url)
    db.flush()

    short_url = f"{request.base_url}{alias}"

    record = IdempotencyKey(
        key=idempotency_key,
        request_hash=hashlib.sha256(long_url.encode("utf-8")).hexdigest(),
        response=short_url,
    )
    db.add(record)
    db.commit()

    return {"short_url": short_url, "alias": alias, "long_url": long_url}


@app.get("/{alias}", include_in_schema=False)
def redirect(alias: str, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    rate_limit(ip, limit=100)

    url_record = db.query(URL).filter(URL.alias == alias).first()
    if not url_record:
        raise HTTPException(status_code=404, detail="Alias not found")

    url_record.clicks += 1
    db.commit()
    return RedirectResponse(url=url_record.long_url, status_code=status.HTTP_302_FOUND)


@app.get("/info/{alias}")
def info(alias: str, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    rate_limit(ip, limit=50)

    url_record = db.query(URL).filter(URL.alias == alias).first()
    if not url_record:
        raise HTTPException(status_code=404, detail="Alias not found")

    return {
        "alias": url_record.alias,
        "long_url": url_record.long_url,
        "created_at": url_record.created_at,
        "clicks": url_record.clicks,
    }


@app.delete("/delete/{alias}")
def delete(alias: str, db: Session = Depends(get_db)):
    url_record = db.query(URL).filter(URL.alias == alias).first()
    if not url_record:
        return {"message": "Already deleted or not found"}

    db.delete(url_record)
    db.commit()
    return {"message": "Short URL deleted successfully", "alias": alias}
