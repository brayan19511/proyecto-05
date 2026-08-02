from pathlib import Path

import duckdb


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def register_parquet_or_empty(
    con: duckdb.DuckDBPyConnection,
    *,
    view_name: str,
    path: Path,
    empty_select_sql: str,
) -> None:
    if path.exists():
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW {view_name} AS
            SELECT * FROM read_parquet('{sql_path(path)}')
            """
        )
        return

    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW {view_name} AS
        {empty_select_sql}
        WHERE FALSE
        """
    )
