from contextlib import asynccontextmanager

from database import Base, engine
from fastapi import FastAPI
from routers.images import router as images_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(images_router)


@app.get("/")
async def root():
    return {"message": "FastAPI"}
