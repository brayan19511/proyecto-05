# app\models\sap\models..py
from dataclasses import dataclass

@dataclass(slots=True)
class SAPCredentials:
    company: str
    user_name: str
    password: str