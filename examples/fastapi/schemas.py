from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    city: str = Field(..., examples=["Kyoto"])
    country: str = Field(..., examples=["JP"])


class AddressOut(AddressCreate):
    _id: int
    _version: int


class UserCreate(BaseModel):
    name: str
    age: int = Field(ge=0)
    address_id: Optional[int] = Field(default=None, description="Existing address id to link")


class UserPatch(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0)
    address_id: Optional[int] = Field(default=None, description="Set to null to unlink")


class UserOut(BaseModel):
    _id: int
    _version: int
    name: str
    age: int
    address: Optional[dict] = None
    orders: list[dict] = []


class OrderCreate(BaseModel):
    total: float = Field(ge=0)
    note: str = ""


class OrderOut(OrderCreate):
    _id: int
    _version: int


class OkOut(BaseModel):
    ok: bool = True

