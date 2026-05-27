# app/api/provisions/concepts/concepts_service.py
from app.api.master.master_service import MasterService
from app.api.provisions.concepts.concepts_repository import ConceptsRepository
from app.api.provisions.concepts.concepts_schema import ConceptCreateRequest, ConceptUpdateRequest

class ConceptsService:
    def __init__(self, db):
        self.db = db
        self.repository = ConceptsRepository(db)

    def get_concepts(self, search: str | None = None):
        return self.repository.get_concepts(search=search)
    def get_concept_by_id(self, concept_id: int):
        return self.repository.get_concept_by_id(concept_id)
    def create_concept(self, concept_data:ConceptCreateRequest, current_user_id: int):
        self.validate_company(concept_data.company_id)
        return self.repository.create_concept(concept_data, current_user_id)
    def update_concept(self, concept_id: int, concept_data:ConceptUpdateRequest, current_user_id: int):
        self.validate_concept(concept_id)
        if concept_data.company_id:
            self.validate_company(concept_data.company_id)
        return self.repository.update_concept(concept_id, concept_data, current_user_id)
    def delete_concept(self, concept_id: int, current_user_id: int):
        self.validate_concept(concept_id)
        return self.repository.delete_concept(concept_id, current_user_id)

    def validate_company(self, company_id: int):
        masterService = MasterService(self.db)
        company = masterService.get_company_by_id(company_id)
        if not company:
            raise ValueError("Company not found")
    def validate_concept(self, concept_id: int):
        concept = self.get_concept_by_id(concept_id)
        if not concept:
            raise ValueError("Concept not found")