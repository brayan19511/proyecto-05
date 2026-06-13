import requests
import pandas as pd


class TicketsClient:
    def __init__(self):
        self.url = (
            "http://161.132.103.178:5077/sdeskCOOLBOX/reports/requests_all_v2.php"
        )

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_", regex=False)
            .str.replace("ñ", "n", regex=False)
            .str.replace("á", "a", regex=False)
            .str.replace("é", "e", regex=False)
            .str.replace("í", "i", regex=False)
            .str.replace("ó", "o", regex=False)
            .str.replace("ú", "u", regex=False)
            .str.replace("/", "_", regex=False)
            .str.replace("__", "_", regex=False)
        )
        return df

    def get_tickets(self, start_date: str, end_date: str):
        payload = {
            "fecha_inicio": start_date,
            "fecha_final": end_date,
            "request0": "0",
            "tier0": "0",
        }

        try:
            response = requests.post(
                self.url,
                data=payload,
                timeout=30,
            )

            response.raise_for_status()

            tables = pd.read_html(response.text)

            if not tables:
                raise ValueError(
                    "No se encontraron tablas HTML en la respuesta."
                )

            df = self._normalize_columns(tables[0])

            return df

        except requests.RequestException as e:
            raise ConnectionError(
                f"Error al consultar Tickets: {e}"
            ) from e

        except ValueError as e:
            raise ValueError(
                f"Error procesando la respuesta: {e}"
            ) from e