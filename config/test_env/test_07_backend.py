
print("\n=== FASTAPI + HTTPX ===")
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.testclient import TestClient

app = FastAPI()

class Item(BaseModel):
    name: str
    value: int

@app.post("/items")
def create_item(item: Item):
    return {"name": item.name, "value": item.value, "result": item.value * 2}

with TestClient(app) as client:
    response = client.post(
        "/items",
        json={"name": "test", "value": 21},
    )
    print("FastAPI:", response.status_code, response.json())
    assert response.status_code == 200
    assert response.json()["result"] == 42

print("\n=== SQLALCHEMY ===")
from sqlalchemy import create_engine, text

engine = create_engine("sqlite+pysqlite:///:memory:")

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE measurements (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL
        )
    """))
    conn.execute(
        text("INSERT INTO measurements (name, value) VALUES (:n, :v)"),
        [{"n": "temperature", "v": 21.5},
         {"n": "humidity", "v": 48.0}],
    )
    rows = conn.execute(
        text("SELECT name, value FROM measurements ORDER BY id")
    ).all()

print("SQL rows:", rows)
assert len(rows) == 2
assert rows[0].name == "temperature"

print("\n=== ALEMBIC ===")
from alembic.config import Config
from alembic.script import ScriptDirectory

config = Config()
print("Alembic Config:", config is not None)
print("Alembic version:", __import__("alembic").__version__)

print("\n=== CELERY ===")
from celery import Celery

celery_app = Celery("local_test", broker="memory://")
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

@celery_app.task
def multiply(a, b):
    return a * b

result = multiply.delay(6, 7)
print("Celery result:", result.get())
assert result.get() == 42

print("\n=== REDIS CLIENT ===")
import redis

redis_client = redis.Redis.from_url("redis://localhost:6379/0")
print("Redis client created:", redis_client.connection_pool is not None)
redis_client.close()

print("\n=== POSTGRES DRIVERS ===")
import asyncpg
import psycopg

print("asyncpg:", asyncpg.__version__)
print("psycopg:", psycopg.__version__)

print("\n=== GRPC ===")
import grpc
from concurrent import futures

def echo_handler(request, context):
    return request

handler = grpc.method_handlers_generic_handler(
    "test.Echo",
    {
        "Echo": grpc.unary_unary_rpc_method_handler(
            echo_handler,
            request_deserializer=lambda x: x,
            response_serializer=lambda x: x,
        )
    },
)

server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
server.add_generic_rpc_handlers((handler,))
port = server.add_insecure_port("127.0.0.1:0")
server.start()

try:
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    call = channel.unary_unary(
        "/test.Echo/Echo",
        request_serializer=lambda x: x,
        response_deserializer=lambda x: x,
    )
    response = call(b"hello grpc", timeout=3)
    print("gRPC response:", response)
    assert response == b"hello grpc"
    channel.close()
finally:
    server.stop(0).wait()

print("\nALL TESTS PASSED")

