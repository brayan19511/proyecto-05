import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import UploadFile


def normalizar_para_busqueda(valor: str) -> str:
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", valor)
        if unicodedata.category(caracter) != "Mn"
    )
    return sin_tildes.upper()


def normalizar_texto(valor: str | None) -> str:
    if not valor:
        return ""
    return re.sub(r"\s+", " ", normalizar_para_busqueda(valor)).strip()


def obtener_valor(contenido: str, campo: str) -> str | None:
    contenido_busqueda = normalizar_para_busqueda(contenido)
    campo_busqueda = normalizar_para_busqueda(campo)
    coincidencia = re.search(
        rf"^{re.escape(campo_busqueda)}\s+(.+)$",
        contenido_busqueda,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not coincidencia:
        return None
    return contenido[coincidencia.start(1) : coincidencia.end(1)].strip()


def normalizar_moneda(moneda: str) -> str:
    moneda_normalizada = moneda.strip().upper().replace(" ", "")
    monedas = {
        "S/": "PEN",
        "S/.": "PEN",
        "PEN": "PEN",
        "SOLES": "PEN",
        "SOL": "PEN",
        "US$": "USD",
        "USD": "USD",
        "$": "USD",
        "DOLARES": "USD",
    }
    return monedas.get(moneda_normalizada, moneda_normalizada)


def extraer_monto(valor: str | None) -> dict[str, Any] | None:
    if not valor:
        return None

    coincidencia = re.match(
        r"^\s*"
        r"(?P<moneda>S\/\.?|US\$|USD|PEN|\$)"
        r"\s*"
        r"(?P<monto>[\d,]+(?:\.\d{1,2})?)"
        r"\s*$",
        valor,
        flags=re.IGNORECASE,
    )
    if not coincidencia:
        return None

    moneda_original = coincidencia.group("moneda")
    monto_texto = coincidencia.group("monto")
    try:
        monto_decimal = Decimal(monto_texto.replace(",", ""))
    except InvalidOperation:
        return None

    return {
        "texto": valor.strip(),
        "moneda_original": moneda_original,
        "moneda": normalizar_moneda(moneda_original),
        "monto": monto_decimal,
    }


class PaymentPdfParser:
    """Extrae datos relevantes desde constancias PDF de pago."""

    def parse(self, file: UploadFile) -> dict[str, Any]:
        resultado = {
            "archivo": file.filename,
            "procesado": False,
            "error": None,
        }
        try:
            self._validate_file(file)
            contenido = self._extract_pdf_text(file)
            datos_operacion = self._extract_operation_data(contenido)
            datos_destino = self._extract_destination_data(contenido)
            self._validate_extracted_data(datos_destino)
            resultado.update(
                {
                    "procesado": True,
                    "datos_operacion": datos_operacion,
                    "datos_destino": datos_destino,
                }
            )
        except Exception as exc:
            resultado["error"] = str(exc)
        finally:
            try:
                file.file.seek(0)
            except Exception:
                pass
        return resultado

    @staticmethod
    def _validate_file(file: UploadFile) -> None:
        content_type = (file.content_type or "").lower()
        filename = (file.filename or "").lower()
        if content_type != "application/pdf" and not filename.endswith(".pdf"):
            raise ValueError("El archivo no es un PDF")

    @staticmethod
    def _extract_pdf_text(file: UploadFile) -> str:
        try:
            import pdfplumber
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Falta instalar pdfplumber para leer archivos PDF"
            ) from exc

        paginas = []
        with pdfplumber.open(file.file) as pdf:
            for pagina in pdf.pages:
                paginas.append(pagina.extract_text() or "")

        contenido = "\n".join(paginas).strip()
        if not contenido:
            raise ValueError(
                "No se pudo extraer texto del PDF. "
                "Es posible que sea un documento escaneado."
            )
        return contenido

    @staticmethod
    def _extract_section(contenido: str, inicio: str, fin: str) -> str:
        contenido_busqueda = normalizar_para_busqueda(contenido)
        inicio_busqueda = normalizar_para_busqueda(inicio)
        fin_busqueda = normalizar_para_busqueda(fin)
        coincidencia = re.search(
            rf"{re.escape(inicio_busqueda)}(.*?)(?:{re.escape(fin_busqueda)}|$)",
            contenido_busqueda,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not coincidencia:
            return ""
        return contenido[coincidencia.start(1) : coincidencia.end(1)].strip()

    def _extract_operation_data(self, contenido: str) -> dict[str, str | None]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la operacion",
            fin="Datos de la cuenta de origen",
        )
        return {
            "fecha_envio": obtener_valor(seccion, "Fecha de envio"),
            "estado": obtener_valor(seccion, "Estado"),
            "fecha_proceso": obtener_valor(seccion, "Fecha de proceso"),
        }

    def _extract_destination_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la cuenta de destino",
            fin="Datos de envio de constancia",
        )
        monto_original = obtener_valor(seccion, "Monto")
        monto_info = extraer_monto(monto_original)
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": obtener_valor(seccion, "Titular"),
            "cuenta": obtener_valor(seccion, "Cuenta"),
            "tipo": obtener_valor(seccion, "Tipo"),
            "referencia": obtener_valor(seccion, "Referencia"),
        }

    @staticmethod
    def _validate_extracted_data(datos_destino: dict) -> None:
        campos_faltantes = []
        if not datos_destino.get("titular"):
            campos_faltantes.append("titular")
        if not datos_destino.get("cuenta"):
            campos_faltantes.append("cuenta")
        if not datos_destino.get("monto_texto"):
            campos_faltantes.append("monto")
        if datos_destino.get("monto_decimal") is None:
            campos_faltantes.append("monto valido")
        if not datos_destino.get("moneda"):
            campos_faltantes.append("moneda")

        if campos_faltantes:
            raise ValueError(
                "No se encontraron o no se pudieron interpretar los campos: "
                + ", ".join(campos_faltantes)
            )
