
from fastapi import APIRouter


router = APIRouter(    prefix="/concepts",    tags=["Provisions"],)


@router.get("/")
async def get_concepts():
    return {"message": "List of concepts"}
@router.post("/")
async def create_concept():
    return {"message": "Concept created"}
@router.get("/{concept_id}")
async def get_concept(concept_id: int):
    return {"message": f"Details of concept {concept_id}"}
@router.put("/{concept_id}")
async def update_concept(concept_id: int):
    return {"message": f"Concept {concept_id} updated"}
@router.delete("/{concept_id}")
async def delete_concept(concept_id: int):
    return {"message": f"Concept {concept_id} deleted"}



