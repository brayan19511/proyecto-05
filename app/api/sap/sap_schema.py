from pydantic import BaseModel


class SAPDocumentResult(BaseModel):
    documento: int | str
    status: str
    status_code: int | None = None
    response: dict | list | str | None = None
    error: str | None = None
class SapServiceDocumentos(BaseModel):
    user: str
    password: str
    database: str

    entidad: str
    action: str

    documentos: list[int]