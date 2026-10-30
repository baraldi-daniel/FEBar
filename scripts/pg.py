"""Helper: abre conexão psycopg no Lakebase usando OAuth do CLI (perfil em DATABRICKS_CONFIG_PROFILE). Uso: python3 pg.py "<sql>" | python3 pg.py -f file.sql"""
import json, os, subprocess, sys, psycopg
# configure via variáveis de ambiente (gerado pelo bootstrap em .env)
P = os.environ["DATABRICKS_CONFIG_PROFILE"]
EP = os.environ["LAKEBASE_ENDPOINT"]
HOST = os.environ["LAKEBASE_HOST"]
USER = os.environ["LAKEBASE_USER"]   # seu e-mail no workspace
def conn(db="databricks_postgres"):
    tok = json.loads(subprocess.check_output(["databricks", "postgres", "generate-database-credential", EP, "-p", P, "-o", "json"]))["token"]
    return psycopg.connect(host=HOST, dbname=db, user=USER, password=tok, sslmode="require", autocommit=True)
if __name__ == "__main__":
    args = sys.argv[1:]
    db = "databricks_postgres"
    if args and args[0].startswith("--db="):
        db = args.pop(0)[5:]
    sql = open(args[1]).read() if args[0] == "-f" else args[0]
    with conn(db) as c:
        cur = c.execute(sql)
        if cur.description:
            for r in cur.fetchall(): print(r)
        else:
            print("OK", cur.statusmessage)
