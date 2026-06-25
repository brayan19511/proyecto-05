# Herramientas ORM

`sqlacodegen` puede generar modelos iniciales desde una base existente:

```bash
sqlacodegen \
  "mssql+pyodbc://usuario:password@servidor/base?driver=ODBC+Driver+17+for+SQL+Server" \
  --tables tabla_1,tabla_2 \
  --outfile generated_models.py
```

El resultado debe revisarse antes de incorporarlo:

- Ajustar nombres y tipos.
- Añadir esquemas.
- Definir relaciones e índices.
- No colocar credenciales reales en comandos versionados.
