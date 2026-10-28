"""Helper: executa SQL num SQL warehouse (perfil em DATABRICKS_CONFIG_PROFILE, warehouse em WAREHOUSE_ID). Uso: python3 sql.py "<sql>" | -f file.sql (statements separados por ';;')"""
import os, sys, time
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"])
WH = os.environ["WAREHOUSE_ID"]
APP_SP = os.getenv("APP_SP_CLIENT_ID", "")  # usado em grants_sp.sql ({{APP_SP}})
def q(sql):
    r = w.statement_execution.execute_statement(warehouse_id=WH, statement=sql, wait_timeout="50s", catalog="dadosapp", schema="fundalis_ia")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2); r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error.message)
    cols = [c.name for c in r.manifest.schema.columns] if r.manifest and r.manifest.schema else []
    return cols, (r.result.data_array or []) if r.result else []
if __name__ == "__main__":
    a = sys.argv[1:]
    stmts = (open(a[1]).read() if a[0] == "-f" else a[0]).replace("{{APP_SP}}", APP_SP).split(";;")
    for s in stmts:
        if not s.strip(): continue
        cols, rows = q(s)
        if cols: print(cols)
        for r in rows[:200]: print(r)
        if not cols: print("OK")
