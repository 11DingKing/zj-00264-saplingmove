from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app import models

from app.routers import nurseries, stocks, plots, allocations, stats

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="云杉苗木调拨管理系统",
    description="祁连山生态修复和三北工程苗木调拨后台管理系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nurseries.router)
app.include_router(stocks.router)
app.include_router(plots.router)
app.include_router(allocations.router)
app.include_router(stats.router)


@app.get("/", tags=["系统"])
def root():
    return {
        "name": "云杉苗木调拨管理系统",
        "version": "1.0.0",
        "description": "祁连山生态修复和三北工程苗木调拨后台管理",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["系统"])
def health_check():
    return {"status": "ok", "message": "服务运行正常"}
