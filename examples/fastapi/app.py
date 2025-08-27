from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, close_db
from .models import User, Address, Order
from sqler.query import SQLerField as F

app = FastAPI(title="SQLer Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_start():
    init_db()  # in-memory; change to on-disk by passing a path


@app.on_event("shutdown")
def on_stop():
    close_db()


@app.post("/addresses")
def create_address(city: str, country: str):
    a = Address(city=city, country=country).save()
    return a.model_dump() | {"_id": a._id}


@app.post("/users")
def create_user(name: str, age: int, address_id: int | None = None):
    u = User(name=name, age=age)
    if address_id is not None:
        addr = Address.from_id(address_id)
        if addr is None:
            raise HTTPException(404, "address not found")
        u.set_address(addr)
    u.save()
    return u.model_dump() | {"_id": u._id}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    u = User.from_id(user_id)
    if u is None:
        raise HTTPException(404)
    return u.model_dump() | {"_id": u._id}


@app.get("/users")
def list_users(
    min_age: int | None = Query(None),
    city: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    qs = User.query()
    if min_age is not None:
        qs = qs.filter(F("age") >= min_age)
    if city:
        qs = qs.filter(User.ref("address").field("city") == city)
    if q:
        qs = qs.filter(F("name").like(f"%{q}%"))
    users = qs.order_by("age").limit(limit).all()
    return [u.model_dump() | {"_id": u._id} for u in users]


@app.post("/orders")
def create_order(total: float, note: str = ""):
    o = Order(total=total, note=note).save()
    return o.model_dump() | {"_id": o._id}


@app.post("/users/{user_id}/orders/{order_id}")
def attach_order(user_id: int, order_id: int):
    u = User.from_id(user_id)
    o = Order.from_id(order_id)
    if not u or not o:
        raise HTTPException(404)
    u.add_order(o)
    u.save()
    return {"ok": True}

