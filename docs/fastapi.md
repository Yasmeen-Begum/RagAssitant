# FastAPI Guide

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints.

## Key Features

* **Fast**: Very high performance, on par with NodeJS and Go (thanks to Starlette and Pydantic). One of the fastest Python frameworks available.
* **Fast to code**: Increase the speed to develop features by about 200% to 300%.
* **Fewer bugs**: Reduce about 40% of human (developer) induced errors.
* **Intuitive**: Great editor support. Completion everywhere. Less time debugging.
* **Easy**: Designed to be easy to use and learn. Less time reading documentation.
* **Short**: Minimize code duplication. Multiple features from each parameter declaration. Fewer bugs.
* **Robust**: Get production-ready code. With automatic interactive documentation.
* **Standards-based**: Based on (and fully compatible with) the open standards for APIs: OpenAPI (previously known as Swagger) and JSON Schema.

## Creating a Simple API

Here is a minimal FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

To run this application, use a production server like Uvicorn:

```bash
uvicorn main:app --reload
```

## Path Parameters

You can declare path "parameters" or "variables" with the same syntax used by Python format strings:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

The value of the path parameter `item_id` will be passed to your function as the argument `item_id`.
FastAPI will automatically parse and validate the path parameter using standard Python type hints. If the type is declared as `int` and the user requests `/items/foo`, FastAPI will return a clear HTTP validation error.

## Query Parameters

When you declare other function parameters that are not part of the path parameters, they are automatically interpreted as "query" parameters:

```python
from typing import Union

@app.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

The query is the set of key-value pairs that go after the `?` in a URL, separated by `&` characters. For example, in `/items/?skip=0&limit=10`, the query parameters are `skip` with a value of `0` and `limit` with a value of `10`.
