Ejemplo de obtener modelos
libreria :
sqlacodegen

```
sqlacodegen "mssql+pyodbc://usuario:password@10.0.0.5/EcommDB?driver=ODBC+Driver+17+for+SQL+Server"   
--tables rappi_sku,mx_rappi_sku --outfile peya_model.py
