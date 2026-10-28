# Google Sheets → Supabase sync

Live project: global-trade-intelligence (cdnzpncsbxavakbvtgem), Mumbai.
Source: https://docs.google.com/spreadsheets/d/1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0/edit
Script: https://script.google.com/home/projects/1LmYrnhhkQVDgud-kxkhV7IpJBFTLDM3KD6ArZ_gVfv-RpKJvXSdMqZKQ/edit
Trigger owner: alphacentauric.ai@gmail.com. This account has authorized Editor access to the source workbook.

Verified initial sync: 2026-10-27 18:10:15 UTC. 30 records (13 importers, 12 exporters, 5 growers/suppliers); values/formulas snapshot of all 13 sheets. Three installable triggers verified: tradeOnEdit, tradeOnChange, tradeReconcile (five minutes).

The Google Sheet is the operational source of truth. This is one-way synchronization, not database-to-sheet writeback. Source IDs in column A identify operational rows, with headers in row 5. Keep IDs stable and unique. Rows without IDs remain in snapshots but are not separate keyed records. Changing an ID is treated as deletion of the old record and insertion of the new one.

The private database keeps sheet_records, change_events and content-addressed sheet_snapshots. Removed rows and sheets are soft-deleted; their old values remain recoverable by an administrator. Snapshots preserve cell values and formulas, not full formatting/charts/Drive permissions. They do not replace the XLSX backup tool or independent offsite backups.

Direct edits and structural changes invoke full-workbook sync. API/script changes are reconciled approximately every five minutes, subject to Google/Supabase availability and quotas. This is not an audit of every intermediate keystroke: rapid missed/API changes may be represented only by their final reconciled state. Snapshots deduplicate identical content. The server rejects duplicate IDs, invalid signatures, expired timestamps and stale versions transactionally. A failed sync does not delete the last good database state.

Private HMAC key: Script Properties TRADE_SIGNING_SECRET and private database sync_sources. Never place it in cells, client code or Git. The backend/.env local recovery copy is gitignored and permission-restricted. The service-role credential never leaves the Edge Function environment. The public endpoint is write-only and HMAC-authenticated; normal anon/authenticated roles cannot execute the database ingest RPC or read private tables.

Monitor Apps Script Executions for failed runs and Project Settings script properties TRADE_LAST_SYNC, TRADE_LAST_ERROR and TRADE_PENDING. No public database read interface is deployed. The standalone script onOpen menu helper is not automatically invoked by this installation; run tradeSyncNow manually in the editor if needed.

Testing: unauthorized HTTP request returned 401. Transactional synthetic SQL tests verified INSERT, UPDATE, DELETE, RESTORE and were rolled back. Initial production import verified from Supabase and installer reported Execution completed. No live business records were modified for testing.

## Discovery integration

The deployed endpoint also accepts crawler-key-signed batches into discovery_leads and returns pending leads to authenticated workbook syncs. Code.gs appends them idempotently to Discovery inbox, then acknowledges delivery. These unverified records do not overwrite the main CRM. Daily cron is configured in .github/workflows/discovery.yml. Direct Meta API crawling remains disabled until authorized credentials/targets are configured.
