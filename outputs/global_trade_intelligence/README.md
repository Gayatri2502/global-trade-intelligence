# Trade Ledger

The local dashboard at http://127.0.0.1:8765 uses Supabase for operational records. Start it with `python3 server.py` or open **Launch Dashboard.command**. The server uses the existing private signing configuration.

- **Refresh records** reads the current database state.
- **Manage records** edits or archives contacts, calls, deals, milestones and cash entries using revision checks.
- **Bulk import** previews CSV or XLSX company rows and inserts new contacts after confirmation.

The [Vercel production dashboard](https://trade-ledger-seven.vercel.app/) serves a public synthetic demo. Live access and edits require a protected server connection. Legacy workbook and Sheets utilities remain in the repository for existing workflows and historical recovery.

## Model additions

- CRM **AX**: qualification date.
- Call log **L:M**: decision-maker reached and qualification outcome.
- Deals **AZ:BN**: supplier key, quantity/unit, business model, contract commission/currency/FX, earned/due dates, earned commission, commission receipts, noncash commission credit adjustments, outstanding commission, completion and next follow-up dates.
- Cash ledger categories **Commission receipt**, **Customer refund** and **Commission refund** keep collections and refunds distinct. Enter refunds as positive Payment events. **Commission receipt** separates commissions from physical-goods customer receipts. Commission receipts do not reduce trade receivables.

Invoiced revenue, cash collected, direct trade contribution, expected pipeline and commission earned/received remain separate measures. Missing histories are shown as unavailable; no synthetic transactions or unsupported trend sparklines are included.

Map markers use published company countries and Natural Earth country label positions, not verified company coordinates. Corridors require actual deal origins and destinations. Boundaries: https://www.naturalearthdata.com/about/terms-of-use/ .
