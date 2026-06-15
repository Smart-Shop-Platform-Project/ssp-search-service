from fastapi import FastAPI
import logging
import sys
from .api.search_routes import router as search_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ssp-search-service")

app = FastAPI(title="SSP Search Service")

app.include_router(search_router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "SSP Search Service is running"}
