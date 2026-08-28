from contextlib import asynccontextmanager

from database import engine
from fastapi import FastAPI
from sqlmodel import SQLModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "FastAPI"}
