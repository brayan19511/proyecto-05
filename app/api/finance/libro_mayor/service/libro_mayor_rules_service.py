# app/api/libro_mayor/rules_engine.py
import pandas as pd

from app.api.finance.libro_mayor.constants import TEXT_SEARCH_COLUMNS
from app.models.finance.libro_mayor_model import ReglasGastos


class LibroMayorRulesService:

    def aplicar(
        self,
        df: pd.DataFrame,
        reglas: list[ReglasGastos],
        user_id: str | None = None,
    ) -> pd.DataFrame:

        if df.empty:
            return df
        self._inicializar_columnas(df, user_id)
        for regla in reglas:
            self._aplicar_regla(df, regla)
        df.drop(
            columns=["_texto_busqueda_lower"],
            inplace=True,
            errors="ignore",
        )

        return df

    def _inicializar_columnas(self, df: pd.DataFrame, user_id: str | None):
        df["_texto_busqueda_lower"] = (
            df.reindex(columns=TEXT_SEARCH_COLUMNS)
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.casefold()
        )

        df["id_regla"] = None
        df["tiene_regla"] = False

        df["codigo"] = "SIN_CLASIFICAR"
        df["subcodigo"] = "OTROS"
        if "nombre_cuenta_asociada" in df.columns:
            df["nombre_cuenta"] = df["nombre_cuenta_asociada"]

        # derivado de cuenta_asociada
        df["tipo_cuenta"] = df["cuenta_asociada"].astype(str).str[:2]

        if "created_by" not in df.columns:
            df["created_by"] = user_id

        df["updated_by"] = user_id

    def _aplicar_regla(self, df: pd.DataFrame, regla: ReglasGastos):

        mask = self._build_mask(df, regla)

        mask &= df["id_regla"].isna()

        if not mask.any():
            return

        df.loc[mask, "id_regla"] = regla.id_regla
        df.loc[mask, "tiene_regla"] = True

        df.loc[mask, "codigo"] = regla.codigo
        df.loc[mask, "subcodigo"] = regla.subcodigo
        df.loc[mask, "nombre_cuenta"] = regla.nombre_cuenta

    def _build_mask(self, df: pd.DataFrame, regla: ReglasGastos):

        mask = pd.Series(True, index=df.index)

        if regla.cuenta:
            mask &= df["cuenta_asociada"] == regla.cuenta

        if regla.cuenta_contrapartida:
            mask &= df["cuenta_contrapartida"] == regla.cuenta_contrapartida

        if regla.centro_costo:
            mask &= df["centro_costo"] == regla.centro_costo

        if regla.filtro_texto:
            texto = regla.filtro_texto.strip().casefold()
            if texto:
                mask &= df["_texto_busqueda_lower"].str.contains(
                    texto,
                    regex=False,
                    na=False,
                )

        if regla.texto_excluido:
            texto = regla.texto_excluido.strip().casefold()
            if texto:
                mask &= ~df["_texto_busqueda_lower"].str.contains(
                    texto,
                    regex=False,
                    na=False,
                )

        if regla.monto_min is not None:
            mask &= df["cargo_abono_ml"] >= regla.monto_min

        if regla.monto_max is not None:
            mask &= df["cargo_abono_ml"] <= regla.monto_max

        return mask

    def reprocesar(
        self,
        df: pd.DataFrame,
        reglas: list[ReglasGastos],
        user_id: str | None = None,
    ):
        if df.empty:
            return df

        self._inicializar_columnas(df, user_id)

        for regla in reglas:
            self._aplicar_regla(df, regla)

        df.drop(
            columns=["_texto_busqueda_lower"],
            inplace=True,
            errors="ignore",
        )

        return df
