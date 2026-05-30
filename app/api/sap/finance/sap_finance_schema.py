# app\api\sap\schemas\sap_finance_schema.py

from datetime import date, datetime
from pydantic import BaseModel, field_validator

class LibroMayorRequest(BaseModel):

    start_date: date
    end_date: date
    account: str
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v.strip():
            # Lista de formatos que quieres soportar
            formats = [
                "%d/%m/%Y",  # 16/01/2002
                "%Y-%m-%d",  # 2002-01-16
                "%Y/%m/%d",  # 2002/01/16 (El que quieres agregar)
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            
            # Si llega aquí es porque no coincidió con ninguno
            raise ValueError("Formato de fecha no reconocido. Use DD/MM/YYYY o YYYY-MM-DD")