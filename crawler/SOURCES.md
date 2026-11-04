# Source review and schedule

The enabled adapter reads curated company-owned contact pages from `config.json`. It checks robots rules, limits requests, and accepts publicly listed business channels. Unreviewed search results are excluded from automatic ingestion. New leads are unverified. The workflow signs batches using the existing crawler secret and writes directly into the operational ledger.

Configure local run times, weekdays (Monday = 0), and timezone in `schedule.json`. GitHub Actions checks twice an hour and supports Run workflow for an immediate pass. Runs may start late if GitHub delays a scheduled job. The latest due slot is recovered after a missed check. Supabase persists run completion and counts. The workflow concurrency group prevents overlapping GitHub runs. The database transaction makes retries of a saved run idempotent. Failed slots are retried on subsequent checks until a newer slot becomes due. Page-level resume and exact-minute scheduling are not implemented.

## Requested provider review

| Provider | Evidence or collection limitation | Adapter next step |
| --- | --- | --- |
| Export.gov | [ITA exporter services](https://www.trade.gov/services-current-exporters) describes introductions and assistance. No company contact feed confirmed. | Add an authorized trade lead dataset if available. |
| Trade Helpdesk | [Global Trade Helpdesk](https://globaltradehelpdesk.org/) serves a JavaScript application. No confirmed company contact export. The EU Trade Helpdesk is a separate service in Access2Markets. | Confirm the intended portal and documented export. |
| India Trade Portal | [Official portal description](https://www.hciwellington.gov.in/page/trade-services/) describes tariffs, regulations, statistics and directory links. | Review linked company directories individually before enabling them. |
| Trade and Investment Queensland | [Public exhibitor directory](https://www.tiq.qld.gov.au/getmedia/2115b05f-73a2-469d-8b99-da6f0f420097/Gulfood-2026-Exhibitor-Directory-26-013_1.pdf) is indexed, but direct automation hit a browser checkpoint. | Use an authorized feed or accessible publisher-provided export. |
| Export New Zealand | [Public site](https://exportnz.org.nz/) offers exporter support. Its contact page lists its own offices. | Confirm an authorized member directory feed. |
| Business.gov.hk | The supplied domain could not be opened in the inspection environment. No eligible company feed confirmed. | Confirm the official endpoint and reuse terms. |
| Alibaba | [Public marketplace](https://www.alibaba.com/) exposes supplier discovery. No authorized bulk contact interface confirmed. | Add a connector only for an approved integration. |
| Global Sources | Inspection returned HTTP 429. | Use a provider-approved feed or API. |
| IndiaMART | Public inspection was inaccessible. Seller-lead integrations should be scoped to the account's own authorized leads. | Obtain written authorization or an eligible API contract. |
| Volza | [Documented shipment API](https://docs.volza.com/) requires authorized account configuration. | Implement pagination and field mapping against the subscribed endpoint and sample response. |
| Trade Genius | [Vendor site](https://tradegeniusglobal.in/) advertises trade data and lead products. No public API authorization verified. | Obtain a licensed dataset or API. |
| Pangea by Quartile | Provider and endpoint could not be uniquely verified. | Supply the exact vendor URL and permitted access method. |
| Export Genius | Vendor site returned HTTP 403. | Use a licensed API or export. |
| Made in India | Provider name is ambiguous and the candidate domain was inaccessible. | Identify the intended directory URL and permissions. |
| Kompass | [Public directory category](https://in.kompass.com/a/importers-and-exporters/81100/) shows company listings. Automated reuse permission was not verified. | Use a licensed business data feed. |
| Yellow Pages Worldwide | No single national directory or rights holder was specified. | Choose exact country directories with permitted access. |
| Importers Directory | No unique URL supplied. | Verify the directory and its access rules. |
| International Business Directories | Describes a category rather than a specific provider. | Identify each URL before writing an adapter. |

Add source-specific fetch, pagination and parsing through the dispatch in `schedule.py` only after verifying permissions and sample records. Existing contacts retain populated fields; the ingestion records source URLs and fills missing fields. Deduplication uses the stable source ID and normalized company name plus country. It does not resolve renamed companies or subsidiaries automatically.
