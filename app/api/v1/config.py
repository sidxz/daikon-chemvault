from fastapi import APIRouter


router = APIRouter()

@router.get("/version")
async def version():
    return {"version": "1.2.1"}
