from fastapi import APIRouter, Depends, Query
from app.schemas.query_schema import QueryRequest
from app.services.query_service import clear_top_queries, process_query, top_queries
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/query")
def query(data: QueryRequest, user=Depends(get_current_user)):
    return process_query(data.query, user)


@router.get("/queries/top")
def get_top_queries(
    limit: int = Query(default=20, ge=1, le=20),
    user=Depends(get_current_user),
):
    return {"queries": top_queries(user, limit)}


@router.delete("/queries/top")
def clear_recent_queries(user=Depends(get_current_user)):
    deleted_count = clear_top_queries(user)
    return {"message": "Recent queries cleared", "deleted_count": deleted_count}

