# Global Trade Intelligence

Private import/export operating workbook, trading dashboard, Google Sheets synchronization, Supabase audit storage and scheduled public-business discovery.

## Live workbook

https://docs.google.com/spreadsheets/d/1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0/edit

Google Sheets is the operational source of truth. The `data/Trade_Business_Dashboard.xlsx` file is a dated export, not a live connection to Google Sheets. Export the Sheet again when you need an updated Excel file. Existing formulas, contact IDs, call tracking, deals and financial schedules remain in the workbook.

## Run locally

Python 3.12+ is sufficient; the application and crawler use the standard library.

```sh
python3 outputs/global_trade_intelligence/server.py --open
python3 -m unittest discover -s crawler -p 'test_*.py'
python3 crawler/run.py --dry-run
```

The local dashboard binds only to `127.0.0.1:8765`. It reads the saved Excel file; it does not expose the database or a public website. For an explicit workbook use the `TRADE_WORKBOOK` environment variable. Preserve the folder structure when cloning.

## Cloud synchronization

The authorized Apps Script in `backend/Code.gs` sends signed updates to the deployed Supabase `trade-sync` endpoint. The database stores source records, changes and values/formulas snapshots. Deletions are recoverable soft deletions. Read `backend/README.md` for synchronization limits and recovery details. Secrets belong in Script Properties, private database configuration or encrypted GitHub Actions secrets, never committed files.

## Scheduled discovery

GitHub Actions runs `crawler/run.py` daily at **08:00 Asia/Kolkata** (02:30 UTC) and can be run manually from Actions. The job has a ten-minute timeout, at most 30 domains and three pages per domain. It checks robots.txt, refuses non-public network addresses, pauses between requests, stops on access blocks, and stores provenance and an Unverified status. A separate crawler signing key can only ingest discovery leads; it cannot overwrite workbook records.

The crawler starts from the reviewed sources in `crawler/config.json`, follows same-domain Contact/About links and tries three public search RSS queries. Search results are best effort and may be unavailable. It extracts published business email and explicit telephone links; it does not guess phone numbers from quantities or identifiers. Deduplication is by business domain, so separate branches on one domain are intentionally combined pending human review.

Discovered leads go to the private `discovery_leads` table, then the workbook's **Discovery inbox** on the next successful Apps Script sync (normally within five minutes). They are not automatically promoted to verified Importers/Exporters. The inbox is idempotent by Discovery ID. Acknowledgements are sent only after rows are saved.

## Social-platform status

Public website links to social profiles are saved as evidence. **Direct Instagram/Facebook API collection is not active without your authorized Meta API credentials and allowed targets.** Add a Meta token as the `META_ACCESS_TOKEN` repository secret, an applicable supported Graph version as `META_GRAPH_VERSION`, and permitted page IDs/usernames in the config. Instagram Business Discovery also needs `META_IG_BUSINESS_ID`. The integration uses official Graph requests and does not attempt login bypass, private groups, protected profiles or anti-bot circumvention. It cannot crawl every social-media account.

## Cost and data quality

The database project was quoted at $0/month. GitHub Actions uses the account's included private-repository allowance; no paid crawler API or trial is enabled. Daily runs are bounded, but platform quotas and availability still apply. Keep spending limits at zero in your account if you require a hard no-charge policy.

Source pages may contain obsolete or incorrect claims. Review identities, contact channels, certifications and commercial suitability before outreach. Published licence claims are not independently verified. No synthetic business transactions are included.

## Repository contents

- `data/`: live-workbook export captured when this repository was prepared.
- `outputs/global_trade_intelligence/`: local dashboard and XLSX reader.
- `backend/`: versioned SQL, deployed Edge Function source and Apps Script source.
- `crawler/`: public web discovery, authorized social API adapters, configuration and tests.
- `.github/workflows/discovery.yml`: daily cron and manual execution.

This repository is private and contains business data. Do not make it public without reviewing and removing that data. It is not an independent guarantee against data loss; retain separate exports and restore-tested backups.
