# app/models/__init__.py
from app.core.db_postgres import Base # Importas tu Base
from .security import Auth, Role, UserRole
from .user import Information

# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = ["Base", "Auth", "Role", "UserRole", "Information"]