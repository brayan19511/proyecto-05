# app\api\sap\service\sap_batch_service.py
from contextvars import copy_context

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from app.api.sap.service.sap_service_client import (SAPServiceLayerClient)

from app.core.exceptions import (
    SAPAuthenticationError,
    SAPConnectionError,
    SAPRequestError,
)

from app.core.audit_utils import add_step
from app.models.sap.sap_models import SAPCredentials



def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]
    
class SapBatchService:

    def __init__(
        self,
        credentials: SAPCredentials,
        max_workers: int = 4,
        batch_size: int = 25,
    ):
        self.credentials = credentials
        self.max_workers = max_workers
        self.batch_size = batch_size
        
    def _build_client(
        self,
    ) -> SAPServiceLayerClient:

        return SAPServiceLayerClient(
            company=self.credentials.company,
            user_name=self.credentials.user_name,
            password=self.credentials.password,
        )
    def execute(self, request):

        documentos = request.documentos

        lotes = list(
            chunked(
                documentos,
                self.batch_size,
            )
        )

        resultados = []

        success = 0
        failed = 0
        add_step(
            "SAP Batch",
            "INFO",
            f"Procesando {len(documentos)} documentos",
        )
        with ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:

            futures = { }
            for lote in lotes:

                ctx = copy_context()

                future = executor.submit(
                    ctx.run,
                    self._process_batch,
                    lote,
                    request.entidad,
                    request.action,
                )

                futures[future] = lote

            for future in as_completed(
                futures
            ):

                lote_resultado = future.result()

                for item in lote_resultado:

                    resultados.append(item)

                    if item["status"] == "ok":
                        success += 1
                    else:
                        failed += 1
        add_step(
            "SAP Batch",
            "SUCCESS",
            f"OK={success} ERROR={failed}",
        )
        return {
            "total": len(documentos),
            "success": success,
            "failed": failed,
            "results": resultados,
        }
    
    def _process_batch(
        self,
        documentos,
        entidad,
        action,
    ):

        resultados = []

        with self._build_client() as client:

            for documento in documentos:

                endpoint = (
                    f"{entidad}({documento})/{action}"
                )

                try:

                    response = client.post(
                        endpoint
                    )

                    resultados.append(
                        {
                            "documento": documento,
                            "status": "ok",
                            "response": response,
                        }
                    )

                except SAPRequestError as exc:

                    resultados.append(
                        {
                            "documento": documento,
                            "status": "error",
                            "status_code": exc.status_code,
                            "error": exc.detail,
                        }
                    )

                except Exception as exc:

                    resultados.append(
                        {
                            "documento": documento,
                            "status": "error",
                            "status_code": 500,
                            "error": str(exc),
                        }
                    )

        return resultados