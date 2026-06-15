from fastapi import APIRouter, HTTPException
from ..services.search_service import SearchService
from typing import List

router = APIRouter()
search_service = SearchService()

@router.get("/search", tags=["Search"])
async def search_products(query: str, size: int = 10):
    try:
        return await search_service.search_products(query, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
