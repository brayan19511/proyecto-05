

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ConceptCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    active: Optional[bool] = True
    code_sap: Optional[str] = None
    company_id: Optional[int] = Field(default=None, gt=0)
    
class ConceptUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    code_sap: Optional[str] = None
    company_id: Optional[int] = Field(default=None, gt=0)
class ConceptResponse(ConceptCreateRequest):
    id: int
    company_code: str | None
    model_config = ConfigDict(from_attributes=True)
class ConceptListResponse(BaseModel):
    concepts: list[ConceptResponse]
