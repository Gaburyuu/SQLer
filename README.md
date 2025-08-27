# SQLer

**A simple, flexible, and powerful micro-ORM for storing and querying JSON documents in SQLite.**

SQLer is a Python library that provides a simple and intuitive way to work with JSON data in a SQLite database. It's designed to be a lightweight alternative to full-fledged ORMs, offering a balance of power and simplicity. It is heavily inspired by TinyDB and other similar document databases.

## Features

- **Pydantic-like Model Persistence:** Store and retrieve Pydantic-like models (or any dictionary) as JSON documents.
- **Automatic Table Creation:** Tables are created automatically when you first insert a document.
- **Flexible Querying:** Build complex queries using a fluent API with `SQLerField` and `SQLerQuery`.
- **JSON Field Indexing:** Create indexes on JSON fields for faster queries.
- **In-Memory and On-Disk Databases:** Use an in-memory database for testing or an on-disk database for persistence.
- **Context Manager Support:** The `SQLiteAdapter` can be used as a context manager to automatically handle connections and transactions.

## Installation

```bash
pip install sqler
```

## Usage

### Basic Usage

```python
from sqler import SQLerDB

# Create an in-memory database
db = SQLerDB.in_memory()

# Insert a document
db.insert_document("users", {"name": "John Doe", "age": 30})

# Find a document
user = db.find_document("users", 1)
print(user)

# Close the connection
db.close()
```

### Model Layer (Pydantic v2)

Use `SQLerModel` to define models that persist as JSON documents, with convenience CRUD and query helpers returning model instances.

```python
from sqler import SQLerDB, SQLerModel
from sqler.query import SQLerField as F

class User(SQLerModel):
    name: str
    age: int

db = SQLerDB.in_memory()
User.set_db(db)  # binds the model to a table named "users"

# Create and save
u = User(name="Alice", age=30)
u.save()
print(u._id)

# Query as models
adults = User.query().filter(F("age") >= 18).order_by("age").all()
print([a.name for a in adults])

# Refresh and delete
u.age = 31
u.save()
u.refresh()
u.delete()

db.close()
```

### Safe Model (Optimistic Locking)

Use `SQLerSafeModel` for opt‑in concurrency safety. New rows start with `_version = 0`. Updates require the current `_version` and atomically bump it on success; stale updates raise `StaleVersionError`.

```python
from sqler import SQLerDB, SQLerSafeModel, StaleVersionError

class Account(SQLerSafeModel):
    owner: str
    balance: int

db = SQLerDB.on_disk("bank.db")
Account.set_db(db)  # adds a `_version` column if missing

acc = Account(owner="Ada", balance=100)
acc.save()                 # _version == 0

# Normal update → bumps version
acc.balance = 120
acc.save()                 # _version == 1

# Stale update example
try:
    db.adapter.execute(
        "UPDATE accounts SET _version = _version + 1 WHERE _id = ?;", [acc._id]
    )
    db.adapter.commit()
    acc.balance = 130
    acc.save()             # raises StaleVersionError
except StaleVersionError:
    acc.refresh()          # reload data + _version

db.close()
```

Notes:
- `query()/filter()/order_by()/limit()` work the same for `SQLerSafeModel` as for `SQLerModel`.
- Query results don’t include `_version`; call `.refresh()` on an instance if you need the latest version.

### Model Indexes & Table Naming

Models persist into a default table name derived from the class: lowercase plural of the class name (e.g., `User` → `users`). You can override this in `set_db`.

```python
from sqler import SQLerDB, SQLerModel

class User(SQLerModel):
    name: str
    age: int

db = SQLerDB.on_disk("app.db")

# Default table name: "users"
User.set_db(db)

# Or override the table name
# User.set_db(db, table="people")

# Create indexes via the model
User.add_index("age")                       # json_extract(data, '$.age')
User.add_index("email", unique=True)        # unique JSON index
User.add_index(
    "meta.level",
    where="json_extract(data, '$.meta.level') IS NOT NULL",
)

# Note: Fields starting with '_' are treated as literal columns (e.g., "_id").
# For normal model fields, you can just pass the JSON path like "meta.level".
```

### Index Guidance

- Index fields you frequently filter/sort on, especially JSON paths used in `filter(...)` and `order_by(...)`.
- For arrays queried via `contains()/isin()` or `.any()`, consider indexing the scalar field you compare on (e.g., `items[].sku` → index `items.sku`).
- Safe models add a `_version` column; you normally don’t index it unless you query by version.
- Use conditional (partial) indices with `where=` to keep indices small and effective.

### Querying

```python
from sqler import SQLerDB
from sqler.query import SQLerField

# Create an on-disk database
db = SQLerDB.on_disk("my_database.db")

# Insert some documents
db.insert_document("users", {"name": "John Doe", "age": 30, "city": "New York"})
db.insert_document("users", {"name": "Jane Doe", "age": 25, "city": "London"})
db.insert_document("users", {"name": "Peter Jones", "age": 35, "city": "New York"})

# Create a query
User = SQLerField
query = db.query("users").filter(User("city") == "New York")

# Get all users in New York (JSON strings)
users_json = query.all()
print(users_json)

# Or get parsed dicts with `_id` attached
users = query.all_dicts()
print(users)

# Get the first user in New York as a parsed dict
user = query.first_dict()
print(user)

# Get the number of users in New York
count = query.count()
print(count)

# Close the connection
db.close()
```

### Advanced Querying

```python
from sqler import SQLerDB
from sqler.query import SQLerField

db = SQLerDB.in_memory()

db.insert_document("products", {"name": "Laptop", "price": 1000, "tags": ["electronics", "computers"]})
db.insert_document("products", {"name": "Mouse", "price": 50, "tags": ["electronics", "accessories"]})
db.insert_document("products", {"name": "Keyboard", "price": 100, "tags": ["electronics", "accessories"]})

# Find all products with a price greater than 100
Product = SQLerField
query = db.query("products").filter(Product("price") > 100)
products = query.all()
print(products)

# Find all products that have the "electronics" tag
query = db.query("products").filter(Product("tags").contains("electronics"))
products = query.all()
print(products)

# Find all products with a price between 50 and 150
query = db.query("products").filter((Product("price") >= 50) & (Product("price") <= 150))
products = query.all()
print(products)

db.close()
```

### Indexes

```python
from sqler import SQLerDB

db = SQLerDB.on_disk("my_database.db")

# Create an index on a JSON field for faster queries
db.create_index("users", "city")  # -> uses json_extract(data, '$.city')

# Unique/conditional index examples
db.create_index("users", "email", unique=True)
db.create_index("users", "age", where="json_extract(data, '$.age') IS NOT NULL")
```

### Arrays of Objects with .any()

When you have arrays of objects, use `.any()` to filter within them efficiently (internally uses `json_each` joins):

```python
from sqler import SQLerDB
from sqler.query import SQLerField as F

db = SQLerDB.in_memory()

db.insert_document("orders", {
    "order_id": 1,
    "items": [
        {"sku": "A1", "qty": 2},
        {"sku": "B2", "qty": 5},
    ]
})

# Find orders where any item has qty > 3
q = db.query("orders").filter(F(["items"]).any()["qty"] > 3)
print(q.all_dicts())  # returns the matching orders as dicts
```

### Return Types

- `query.all()` and `query.first()` return raw JSON strings from SQLite.
- Use `query.all_dicts()` and `query.first_dict()` to get parsed Python dicts with `_id` included.

This split lets you choose zero-copy raw reads (strings) or convenient parsed objects.

### Testing

Run the test suite with uv:

```
uv run -q pytest -q
```

### Contributing & Style

- Read the style guide: see `STYLE_GUIDE.md`.
- Format and lint:
  - `uv run ruff format .`
  - `uv run ruff check .`
- Run tests with coverage (optional gate):
  - `uv run pytest -q --cov=src --cov-report=term-missing --cov-fail-under=90`

### Async Quickstart

Use the async adapter/DB/model for non-blocking workflows. The APIs mirror the sync counterparts.

```python
import asyncio
from sqler import AsyncSQLiteAdapter, AsyncSQLerDB, AsyncSQLerModel
from sqler.query import SQLerField as F

class AUser(AsyncSQLerModel):
    name: str
    age: int

async def main():
    db = AsyncSQLerDB.in_memory()
    await db.connect()
    AUser.set_db(db)

    u = AUser(name="Ada", age=36)
    await u.save()

    adults = await AUser.query().filter(F("age") >= 18).order_by("age").all()
    print([a.name for a in adults])

    await db.close()

asyncio.run(main())
```
