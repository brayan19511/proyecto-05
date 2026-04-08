from fastapi import APIRouter


router = APIRouter()


@router.get("/verify")
async def verify():
    return {"message": "Verification successful"}