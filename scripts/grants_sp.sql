GRANT USE CATALOG ON CATALOG dadosapp TO `{{APP_SP}}`;;
GRANT USE SCHEMA, SELECT, EXECUTE, READ VOLUME, WRITE VOLUME ON SCHEMA dadosapp.fundalis_ia TO `{{APP_SP}}`;;
GRANT MODIFY ON TABLE dadosapp.fundalis_ia.documentos TO `{{APP_SP}}`;;
GRANT MODIFY ON TABLE dadosapp.fundalis_ia.documentos_chunks TO `{{APP_SP}}`;;
GRANT MODIFY ON TABLE dadosapp.fundalis_ia.perguntas_classificadas TO `{{APP_SP}}`;;
GRANT MODIFY ON TABLE dadosapp.fundalis_ia.pii_access TO `{{APP_SP}}`
