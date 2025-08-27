from typing import Optional, List
from sqler.models import SQLerModel
from sqler.models.ref import as_ref


class Address(SQLerModel):
    city: str
    country: str


class Order(SQLerModel):
    total: float
    note: str


class User(SQLerModel):
    name: str
    age: int
    # reference to Address and list of references to Orders
    address: Optional[dict] = None
    orders: List[dict] = []

    def set_address(self, addr: Address):
        if addr._id is None:
            raise ValueError("Save address first")
        self.address = as_ref(addr)

    def add_order(self, order: Order):
        if order._id is None:
            raise ValueError("Save order first")
        self.orders.append(as_ref(order))

