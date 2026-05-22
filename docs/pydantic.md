# Pydantic Guide

Pydantic is the most widely used data validation library for Python. It is fast, extensible, and integrates perfectly with type hints.

## Why Use Pydantic?

* **Powered by type hints**: Pydantic uses standard Python type hints to define data models. There is no custom DSL or schema configuration language to learn.
* **Speed**: Pydantic's core validation logic is written in Rust, making it extremely fast. It is one of the fastest data validation libraries in Python.
* **IDE Integration**: Because models are standard Python classes, you get auto-completion, linting, and hover definitions in your IDE.
* **Serialization**: Pydantic models can easily be serialized to JSON, dictionaries, and custom data formats.
* **Strict & Lax Mode**: Pydantic can run in strict mode (where types are not coerced) or lax mode (where values like the string "123" are coerced to integer `123`).

## Creating a Pydantic Model

Here is an example of defining a simple Pydantic model:

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str = "John Doe"
    signup_ts: Optional[datetime] = None
    friends: List[int] = []
```

## Data Validation

When you instantiate a Pydantic model, it automatically validates all incoming fields against the declared types:

```python
external_data = {
    'id': '123',  # Will be coerced to integer 123
    'signup_ts': '2026-05-18 12:22',
    'friends': [1, 2, '3'],  # '3' will be coerced to 3
}

user = User(**external_data)
print(user.id)          # 123
print(user.friends)     # [1, 2, 3]
```

If validation fails, Pydantic raises a `ValidationError` containing clear, structured error details explaining exactly which fields failed validation and why.

## Field Customization

You can use the `Field` function to add metadata, descriptions, validation constraints, and default factories:

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(..., description="The name of the product")
    price: float = Field(..., gt=0, description="The price must be greater than zero")
    tags: list[str] = Field(default_factory=list)
```

In this example, `price` is validated to be strictly greater than 0 (`gt=0`), and a default empty list is generated dynamically for `tags` if not provided.
