from sqlalchemy.orm import Session

from app.models.finance.libro_mayor_model import ReglasGastos

class ReglasGastosRepository:

    def __init__(self, db: Session):
        self.db = db
    def get_all(self):
        return (
            self.db.query(ReglasGastos)
            .order_by(
                ReglasGastos.prioridad.asc()
            )
            .all()
        )
    def get_by_id(self, id: int) -> ReglasGastos | None:
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.id_regla == id)
            .one_or_none()
        )

    def get_all_active(self) -> list[ReglasGastos]:
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.activo == True)
            .order_by(ReglasGastos.prioridad.asc())
            .all()
        )

    def get_by_account(self, account: str):
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.cuenta.ilike(f"%{account}%"))
            .all()
        )

    def create(self, regla: ReglasGastos):

        self.db.add(regla)
        self.db.commit()
        self.db.refresh(regla)

        return regla

    def update(self, id_regla: int, data: dict):

        regla = self.get_by_id(id_regla)

        if not regla:
            return None

        for key, value in data.items():
            setattr(regla, key, value)

        self.db.commit()
        self.db.refresh(regla)

        return regla

    def delete(self, id_regla: int):

        regla = self.get_by_id(id_regla)

        if not regla:
            return False

        self.db.delete(regla)
        self.db.commit()

        return True
    
