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

# Get all users in New York
users = query.all()
print(users)

# Get the first user in New York
user = query.first()
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
