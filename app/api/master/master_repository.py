# app/api/master/master_repository.py

from sqlalchemy.orm import Session

from app.models.master.master_model import (
    Company,
    Area,
    Currency,
)
from app.models.master.mailing_parameter_model import MailingParameter


class MasterRepository:

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # COMPANY
    # ==========================================

    def get_companies(self, search: str | None = None):

        # Solo registros activos: el borrado es logico (active=False).
        query = self.db.query(Company).filter(Company.active.is_(True))

        if search:
            query = query.filter(
                Company.code.ilike(f"%{search}%")
            )

        return query.all()

    def get_company_by_id(self, company_id: int):

        return (
            self.db.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

    def get_company_by_code(self, code: str):

        return (
            self.db.query(Company)
            .filter(Company.code == code)
            .first()
        )

    def create_company(self, company: Company):

        self.db.add(company)
        return company

    # ==========================================
    # AREA
    # ==========================================

    def get_areas(self, search: str | None = None):

        # Solo registros activos: el borrado es logico (active=False).
        query = self.db.query(Area).filter(Area.active.is_(True))

        if search:
            query = query.filter(
                Area.code.ilike(f"%{search}%")
            )

        return query.all()

    def get_area_by_id(self, area_id: int):

        return (
            self.db.query(Area)
            .filter(Area.id == area_id)
            .first()
        )

    def get_area_by_code(self, code: str):

        return (
            self.db.query(Area)
            .filter(Area.code == code)
            .first()
        )

    def create_area(self, area: Area)->Area:

        self.db.add(area)
        return area

    # ==========================================
    # CURRENCY
    # ==========================================

    def get_currencies(self, search: str | None = None):

        # Solo registros activos: el borrado es logico (active=False).
        query = self.db.query(Currency).filter(Currency.active.is_(True))

        if search:
            query = query.filter(
                Currency.code.ilike(f"%{search}%")
            )

        return query.all()

    def get_currency_by_id(self, currency_id: int):

        return (
            self.db.query(Currency)
            .filter(Currency.id == currency_id)
            .first()
        )

    def get_currency_by_code(self, code: str):

        return (
            self.db.query(Currency)
            .filter(Currency.code == code)
            .first()
        )

    def create_currency(self, currency: Currency):

        self.db.add(currency)
        return currency

    # ==========================================
    # MAILING PARAMETERS
    # ==========================================

    def get_mailing_parameters(self, search: str | None = None):
        # Solo registros activos: el borrado es logico (active=False).
        query = self.db.query(MailingParameter).filter(
            MailingParameter.active.is_(True)
        )
        if search:
            query = query.filter(MailingParameter.name.ilike(f"%{search}%"))
        return query.order_by(MailingParameter.name).all()

    def get_mailing_parameter_by_id(self, parameter_id: int):
        return self.db.get(MailingParameter, parameter_id)

    def get_mailing_parameter_by_name(self, name: str):
        return (
            self.db.query(MailingParameter)
            .filter(MailingParameter.name == name)
            .first()
        )

    def create_mailing_parameter(self, parameter: MailingParameter):
        self.db.add(parameter)
        return parameter

    # ==========================================
    # TRANSACTION
    # ==========================================

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
