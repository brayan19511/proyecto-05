# app/api/master/master_repository.py

from sqlalchemy.orm import Session

from app.models.auth.security_model import UserAreaAccess
from app.models.finance.provision_model import Provision, ProvisionConcept
from app.models.master.master_model import (
    Company,
    Area,
    Currency,
    Module,
)
from app.models.master.mailing_parameter_model import MailingParameter


class MasterRepository:

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # COMPANY
    # ==========================================

    def get_companies(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        # El borrado es logico: por defecto solo se listan los activos.
        query = self.db.query(Company)

        if active is not None:
            query = query.filter(Company.active.is_(active))

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                Company.code.ilike(pattern) | Company.name.ilike(pattern)
            )

        return query.order_by(Company.code).all()

    def get_company_by_id(self, company_id: int, only_active: bool = False):

        query = self.db.query(Company).filter(Company.id == company_id)

        if only_active:
            query = query.filter(Company.active.is_(True))

        return query.first()

    def get_company_by_code(self, code: str):

        return (
            self.db.query(Company)
            .filter(Company.code == code)
            .first()
        )

    def create_company(self, company: Company):

        self.db.add(company)
        return company

    def count_company_dependents(self, company_id: int) -> int:
        """Cuenta registros activos que impiden desactivar la empresa."""
        provisions = (
            self.db.query(Provision)
            .filter(
                Provision.company_id == company_id,
                Provision.active.is_(True),
            )
            .count()
        )

        concepts = (
            self.db.query(ProvisionConcept)
            .filter(
                ProvisionConcept.company_id == company_id,
                ProvisionConcept.active.is_(True),
            )
            .count()
        )

        accesses = (
            self.db.query(UserAreaAccess)
            .filter(
                UserAreaAccess.company_id == company_id,
                UserAreaAccess.active.is_(True),
            )
            .count()
        )

        return provisions + concepts + accesses

    # ==========================================
    # AREA
    # ==========================================

    def get_areas(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        # El borrado es logico: por defecto solo se listan los activos.
        query = self.db.query(Area)

        if active is not None:
            query = query.filter(Area.active.is_(active))

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                Area.code.ilike(pattern) | Area.name.ilike(pattern)
            )

        return query.order_by(Area.code).all()

    def get_area_by_id(self, area_id: int, only_active: bool = False):

        query = self.db.query(Area).filter(Area.id == area_id)

        if only_active:
            query = query.filter(Area.active.is_(True))

        return query.first()

    def get_areas_by_ids(self, area_ids: list[int], only_active: bool = True):

        if not area_ids:
            return []

        query = self.db.query(Area).filter(Area.id.in_(area_ids))

        if only_active:
            query = query.filter(Area.active.is_(True))

        return query.order_by(Area.code).all()

    def get_area_by_code(self, code: str):

        return (
            self.db.query(Area)
            .filter(Area.code == code)
            .first()
        )

    def create_area(self, area: Area) -> Area:

        self.db.add(area)
        return area

    def count_area_dependents(self, area_id: int) -> int:
        """Cuenta registros activos que impiden desactivar el area."""
        provisions = (
            self.db.query(Provision)
            .filter(
                Provision.area_id == area_id,
                Provision.active.is_(True),
            )
            .count()
        )

        accesses = (
            self.db.query(UserAreaAccess)
            .filter(
                UserAreaAccess.area_id == area_id,
                UserAreaAccess.active.is_(True),
            )
            .count()
        )

        return provisions + accesses

    # ==========================================
    # CURRENCY
    # ==========================================

    def get_currencies(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        # El borrado es logico: por defecto solo se listan los activos.
        query = self.db.query(Currency)

        if active is not None:
            query = query.filter(Currency.active.is_(active))

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                Currency.code.ilike(pattern) | Currency.name.ilike(pattern)
            )

        return query.order_by(Currency.code).all()

    def get_currency_by_id(self, currency_id: int, only_active: bool = False):

        query = self.db.query(Currency).filter(Currency.id == currency_id)

        if only_active:
            query = query.filter(Currency.active.is_(True))

        return query.first()

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

    # ==========================================
    # MODULOS
    # ==========================================

    def get_modules(self):
        return self.db.query(Module).order_by(Module.code).all()

    def get_module_by_code(self, code: str):
        return self.db.query(Module).filter(Module.code == code).first()

    def create_module(self, module: Module):
        self.db.add(module)
        return module
