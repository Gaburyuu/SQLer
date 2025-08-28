from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from sqler.models import StaleVersionError
from sqler.query import SQLerField as F

from .db import init_db, close_db, get_db
from .models import Address, Order, User
from .schemas import (
    AddressCreate, AddressOut,
    UserCreate, UserPatch, UserOut,
    OrderCreate, OrderOut, OkOut,
)
from .errors import install_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(os.getenv("SQLER_DB_PATH"))
    yield
    close_db()


app = FastAPI(
    title="SQLer FastAPI Demo",
    version="1.0.0",
    summary="JSON-first micro-ORM on SQLite with WAL + optimistic locking",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    resp: Response = await call_next(request)
    resp.headers["X-Process-Time"] = f"{(time.perf_counter() - start):.6f}s"
    return resp


install_exception_handlers(app)


def _etag(obj_id: int, version: int | None) -> str:
    v = 0 if version is None else int(version)
    return f'W/"{obj_id}-{v}"'


async def _db_call(fn, *args, **kwargs):
    return await run_in_threadpool(fn, *args, **kwargs)


router_users = APIRouter(prefix="/users", tags=["Users"])
router_addresses = APIRouter(prefix="/addresses", tags=["Addresses"])
router_orders = APIRouter(prefix="/orders", tags=["Orders"])


@router_addresses.post("", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_address(payload: AddressCreate):
    a = await _db_call(lambda: Address(**payload.model_dump()).save())
    return AddressOut.model_validate(a.model_dump() | {"_id": a._id, "_version": getattr(a, "_version", 0)})


@router_addresses.get("/{address_id}", response_model=AddressOut)
async def get_address(address_id: int, request: Request, response: Response):
    a = await _db_call(lambda: Address.from_id(address_id))
    if not a:
        raise HTTPException(status_code=404, detail="address not found")
    etag = _etag(a._id, getattr(a, "_version", 0))
    if request.headers.get("if-none-match") == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        response.headers["ETag"] = etag
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return AddressOut.model_validate(a.model_dump() | {"_id": a._id, "_version": getattr(a, "_version", 0)})


@router_users.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate):
    def _create():
        u = User(**payload.model_dump(exclude={"address_id"}))
        if payload.address_id is not None:
            addr = Address.from_id(payload.address_id)
            if not addr:
                raise HTTPException(status_code=404, detail="address not found")
            u.set_address(addr)
        u.save()
        return u
    u = await _db_call(_create)
    return UserOut.model_validate(u.model_dump() | {"_id": u._id, "_version": getattr(u, "_version", 0)})


@router_users.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, request: Request, response: Response):
    u = await _db_call(lambda: User.from_id(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="user not found")
    etag = _etag(u._id, getattr(u, "_version", 0))
    if request.headers.get("if-none-match") == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        response.headers["ETag"] = etag
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return UserOut.model_validate(u.model_dump() | {"_id": u._id, "_version": getattr(u, "_version", 0)})


@router_users.get("", response_model=list[UserOut])
async def list_users(
    min_age: Annotated[int | None, Query(ge=0)] = None,
    city: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(description="substring match on name")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
):
    def _list():
        qs = User.query()
        if min_age is not None:
            qs = qs.filter(F("age") >= min_age)
        if city:
            qs = qs.filter(User.ref("address").field("city") == city)
        if q:
            qs = qs.filter(F("name").like(f"%{q}%"))
        return [
            UserOut.model_validate(u.model_dump() | {"_id": u._id, "_version": getattr(u, "_version", 0)})
            for u in qs.order_by("age").limit(limit).all()
        ]
    return await _db_call(_list)


@router_users.patch("/{user_id}", response_model=UserOut)
async def patch_user(user_id: int, patch: UserPatch, request: Request, response: Response):
    def _patch():
        u = User.from_id(user_id)
        if not u:
            raise HTTPException(status_code=404, detail="user not found")
        current_etag = _etag(u._id, getattr(u, "_version", 0))
        if (if_match := request.headers.get("if-match")) and if_match != current_etag:
            raise HTTPException(status_code=412, detail="If-Match precondition failed")

        data = patch.model_dump(exclude_unset=True)
        if "address_id" in data:
            if data["address_id"] is None:
                u.address = None
            else:
                addr = Address.from_id(data["address_id"])
                if not addr:
                    raise HTTPException(status_code=404, detail="address not found")
                u.set_address(addr)
            data.pop("address_id")

        for k, v in data.items():
            setattr(u, k, v)

        try:
            u.save()
        except StaleVersionError:
            raise HTTPException(status_code=409, detail="version conflict")
        return u

    u = await _db_call(_patch)
    etag = _etag(u._id, getattr(u, "_version", 0))
    response.headers["ETag"] = etag
    return UserOut.model_validate(u.model_dump() | {"_id": u._id, "_version": getattr(u, "_version", 0)})


@router_orders.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate):
    o = await _db_call(lambda: Order(**payload.model_dump()).save())
    return OrderOut.model_validate(o.model_dump() | {"_id": o._id, "_version": getattr(o, "_version", 0)})


@router_users.post("/{user_id}/orders/{order_id}", response_model=OkOut)
async def attach_order(user_id: int, order_id: int):
    def _attach():
        u = User.from_id(user_id)
        o = Order.from_id(order_id)
        if not u or not o:
            raise HTTPException(status_code=404, detail="user or order not found")
        u.add_order(o)
        u.save()
        return {"ok": True}
    return await _db_call(_attach)


app.include_router(router_addresses)
app.include_router(router_users)
app.include_router(router_orders)
