import os, sys, time, json
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"]); S = os.environ["GENIE_SPACE_ID"]
for q in sys.argv[1:]:
    r = w.api_client.do("POST", f"/api/2.0/genie/spaces/{S}/start-conversation", body={"content": q})
    c, m = r["conversation_id"], r["message_id"]
    for _ in range(80):
        msg = w.api_client.do("GET", f"/api/2.0/genie/spaces/{S}/conversations/{c}/messages/{m}")
        if msg["status"] in ("COMPLETED", "FAILED", "CANCELLED"): break
        time.sleep(2)
    print("==", q, msg["status"])
    for a in msg.get("attachments") or []:
        if a.get("text"): print("TXT:", a["text"]["content"][:400])
        if a.get("query"):
            print("SQL:", a["query"]["query"][:300].replace("\n", " "))
            qr = w.api_client.do("GET", f"/api/2.0/genie/spaces/{S}/conversations/{c}/messages/{m}/attachments/{a['attachment_id']}/query-result")
            print("ROWS:", (qr.get("statement_response", {}).get("result", {}).get("data_array") or [])[:4])
