from fastapi import APIRouter
from app.metrics import router as metrics_router

# expose the metrics router under /metrics
router = APIRouter()
router.include_router(metrics_router, prefix="")
