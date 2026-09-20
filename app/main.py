from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import auth, threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Mommy's Time — Community API",
    version="1.0.0",
    description="Backend for the Mommy's Time community (Village) feature. "
    "Users authenticate with Sign in with Apple.",
    lifespan=lifespan,
)

# The iOS app talks to this directly; wide-open CORS is fine and also lets you
# poke the docs from a browser. Tighten origins if you add a web client.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(threads.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "mommys-time-community-api"}
