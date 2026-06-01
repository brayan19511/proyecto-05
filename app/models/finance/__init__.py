# app/models/finance/__init__.py
from .provision_model import Provision,ProvisionConcept,ProvisionDocument,ProvisionStatus
from .libro_mayor_model import LibroMayor,ReglasGastos
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = ["Provision", "ProvisionConcept", "ProvisionDocument", "ProvisionStatus", "LibroMayor", "ReglasGastos"]