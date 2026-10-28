# Private hosted trade dashboard

This directory contains the owner-private Sites Worker deployment. Its source UI remains in `outputs/global_trade_intelligence/`; `python3 hosted/scripts/embed.py` embeds those assets and adapts local help text to the cloud deployment. Run the generator from the full parent repository before packaging this directory.

Build with `bash hosted/scripts/build.sh` and validate with `node hosted/scripts/validate-artifact.mjs`. Keep the Sites project ID in `.openai/hosting.json`. Store `TRADE_OPERATIONS_SECRET` only in private runtime variables. The browser never receives this key. The server reads the canonical model from the signed Supabase endpoint. Sites supplies private sign-in and owner access enforcement.

Operational data and restore instructions are documented in the repository root README. The browser is read-only; editing remains in the existing Google Sheet. The model updates on the GitHub schedule, with daily native Excel backups available through `/api/workbook`.
