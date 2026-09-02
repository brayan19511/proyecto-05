# app\api\sap\service\sap_service_client.py
import threading
import time

import httpx

from app.core.audit_utils import add_step
from app.core.config import settings
from app.core.exceptions import (
    SAPAuthenticationError,
    SAPConnectionError,
    SAPRequestError,
)
from app.core.modules import MODULE_SAP, require_module


class SAPServiceLayerClient:

    def __init__(
        self,
        user_name: str,
        password: str,
        company: str,
        verify_ssl: bool = False,
        timeout: float = 300.0,
    ):
        # Ultima reja del modulo SAP: no se abre ninguna sesion contra Service
        # Layer si el modulo esta apagado, venga de donde venga la llamada.
        require_module(MODULE_SAP)

        self.base_url = settings.SAP_URL.rstrip("/")

        self.user_name = user_name
        self.password = password
        self.company = company

        self.token: str | None = None
        self.lock = threading.Lock()

        self.session = httpx.Client(
            base_url=self.base_url,
            verify=verify_ssl,
            timeout=timeout,
        )

    # ==========================================================
    # LOGIN
    # ==========================================================

    def _login(self) -> None:

        with self.lock:

            if self.token:
                return

            add_step(
                "SAP Login",
                "INFO",
                f"Company: {self.company}",
            )

            try:

                response = self.session.post(
                    "/Login",
                    json={
                        "UserName": self.user_name,
                        "Password": self.password,
                        "CompanyDB": self.company,
                    },
                )

                response.raise_for_status()

                session_id = response.json().get(
                    "SessionId"
                )

                if not session_id:
                    raise SAPAuthenticationError(
                        "SAP no devolvió SessionId"
                    )

                self.token = session_id

                self.session.headers.update(
                    {
                        "Cookie": f"B1SESSION={session_id}"
                    }
                )

                add_step(
                    "SAP Login",
                    "SUCCESS",
                    "Sesión iniciada",
                )

            except httpx.HTTPStatusError as exc:

                add_step(
                    "SAP Login",
                    "ERROR",
                    f"HTTP {exc.response.status_code}",
                )

                if exc.response.status_code == 401:
                    raise SAPAuthenticationError(
                        "Credenciales SAP inválidas"
                    ) from exc

                try:
                    detail = exc.response.json()
                except Exception:
                    detail = exc.response.text

                raise SAPRequestError(
                    status_code=exc.response.status_code,
                    detail=detail,
                ) from exc

            except httpx.RequestError as exc:

                add_step(
                    "SAP Login",
                    "ERROR",
                    "SAP no responde",
                )

                raise SAPConnectionError(
                    "SAP no responde"
                ) from exc

    # ==========================================================
    # LOGOUT
    # ==========================================================

    def logout(self):
        if not self.token:
            return
        try:
            self.session.post("/Logout")
            add_step(
                "SAP Logout",
                "SUCCESS",
                "Sesión cerrada",
            )
        except Exception:
            add_step(
                "SAP Logout",
                "WARNING",
                "No se pudo cerrar sesión",
            )
        finally:
            self.token = None

    # ==========================================================
    # REQUEST
    # ==========================================================

    def _request(
        self,
        method: str,
        endpoint: str,
        retry: bool = True,
        retries=3,
        **kwargs,
    ):

        if not self.token:
            self._login()

        add_step(
            f"SAP {method} {endpoint}",
            "INFO",
            "Enviando solicitud",
        )

        try:

            response = self.session.request(
                method=method,
                url=endpoint,
                **kwargs,
            )

            response.raise_for_status()

            add_step(
                f"SAP {method} {endpoint}",
                "SUCCESS",
                f"HTTP {response.status_code}",
            )

            if not response.content:
                return None

            content_type = response.headers.get(
                "content-type",
                "",
            )

            if (
                "application/json"
                not in content_type.lower()
            ):
                return response.text

            return response.json()

        except httpx.HTTPStatusError as exc:

            status = exc.response.status_code

            # Sesión expirada
            if status == 401 and retry:

                add_step(
                    f"SAP {method} {endpoint}",
                    "WARNING",
                    "Sesión expirada, reintentando login",
                )

                self.token = None

                self.session.headers.pop(
                    "Cookie",
                    None,
                )

                self._login()

                return self._request(
                    method=method,
                    endpoint=endpoint,
                    retry=False,
                    retries=retries,
                    **kwargs,
                )

            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text

            add_step(
                f"SAP {method} {endpoint}",
                "ERROR",
                f"HTTP {status}",
            )

            raise SAPRequestError(
                status_code=status,
                detail=detail,
            ) from exc


        except httpx.RequestError as exc:

            if retries > 0:

                attempt = 4 - retries

                add_step(
                    f"SAP {method} {endpoint}",
                    "WARNING",
                    f"Error de conexión. Intento {attempt} de 3",
                )

                time.sleep(4 - retries)

                return self._request(
                    method=method,
                    endpoint=endpoint,
                    retry=retry,
                    retries=retries - 1,
                    **kwargs,
                )

            add_step(
                f"SAP {method} {endpoint}",
                "ERROR",
                "SAP no responde",
            )

            raise SAPConnectionError(
                "SAP no responde"
            ) from exc

    # ==========================================================
    # MÉTODOS PÚBLICOS
    # ==========================================================

    def get(
        self,
        endpoint: str,
        params: dict | None = None,
    ):
        return self._request(
            "GET",
            endpoint,
            params=params,
        )

    def post(
        self,
        endpoint: str,
        data: dict | None = None,
    ):
        return self._request(
            "POST",
            endpoint,
            json=data,
        )

    def patch(
        self,
        endpoint: str,
        data: dict | None = None,
    ):
        return self._request(
            "PATCH",
            endpoint,
            json=data,
        )

    # def delete(
    #     self,
    #     endpoint: str,
    # ):
    #     return self._request(
    #         "DELETE",
    #         endpoint,
    #     )

    def close(self):

        try:

            if self.token:
                self.logout()

        finally:

            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
