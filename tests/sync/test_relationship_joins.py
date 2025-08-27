from sqler import SQLerDB
from sqler.models import SQLerModel, SQLerModelField as MF
from sqler.query import SQLerField as F


class Address(SQLerModel):
    city: str
    country: str


class User(SQLerModel):
    name: str
    address: Address | None = None


def test_relationship_join_exists_query():
    db = SQLerDB.in_memory(shared=False)
    Address.set_db(db)
    User.set_db(db)

    a1 = Address(city="Kyoto", country="JP").save()
    a2 = Address(city="Osaka", country="JP").save()
    User(name="Alice", address=a1).save()
    User(name="Bob", address=a2).save()
    User(name="Carol", address=a1).save()

    # users where address.city == Kyoto
    qs = User.query().filter(MF(User, ["address", "city"]) == "Kyoto").order_by("name")
    res = qs.all()
    assert [u.name for u in res] == ["Alice", "Carol"]

    # combine with other predicates
    res2 = (
        User.query()
        .filter(MF(User, ["address", "city"]) == "Osaka")
        .exclude(F("name").like("C%"))
        .all()
    )
    assert [u.name for u in res2] == ["Bob"]

