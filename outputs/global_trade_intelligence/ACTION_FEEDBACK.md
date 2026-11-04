# Trade Ledger action inventory

| Surface | Trigger | Progress and completion | Recovery |
| --- | --- | --- | --- |
| Google sign-in | Sign-in link, OAuth callback | Opening status, dashboard on verified session | Dedicated expired, cancelled, denied and failed messages on sign-in |
| Google sign-out | Sign-out form | Disabled button while submitting, redirect to sign-in | Refresh or reopen sign-in after a navigation failure |
| Workspace | Initial load, Refresh records, visible local polling | Skeleton on first read, record status during requests, confirmation on manual refresh | Retry and retain the last loaded view on refresh failure |
| Global Trade Map | Open map | Load boundaries once on demand and confirm readiness | Retry boundary request |
| Contact tables | Inline score, priority, stage, verification and date edits | Disable the field during save, confirm after database reply | Restore current data and report validation, revision or connection issues |
| Contact and operation dialogs | Create/edit company, interaction, opportunity, quotation, deal, milestone, shipment, compliance or cash event | Inline validation and save progress, then refresh views | Keep form open on failure, refresh before retrying ambiguous writes |
| Manual bulk entry | Add multiple contacts | Shared save lifecycle and inserted/skipped counts | Correct invalid input or review skipped duplicates |
| File import | Choose file, preview, commit | Reading and checking phases, preview validation and confirmed import counts | Cancel preview, correct invalid rows or retry the preview |
| Export | Visible CSV | Confirm browser download started | Browser manages final file destination |
| Local UI | Navigation, search, filters, sorting, map controls, details drawers and modal close | Immediate view changes, active navigation and native control/focus feedback | Reset filters or reopen the relevant view |
| Read-only reports | Overview, market, products, country analysis, matching, follow-ups, finance, settings, data quality, guide | Render from the current model and active filters | Refresh the model |
| External GitHub workflows | Scheduled discovery and operations/backup | Execution status in GitHub Actions | Review or rerun in GitHub. The dashboard has no job-status API. |

The shared request utility owns timeout, abort handling and response normalization. UI feedback uses polite live regions and assertive failures, with motion disabled under reduced-motion preferences. Same-origin ledger operations retain revision checks. Read requests can be retried explicitly. A timed-out mutation can have reached the database, so its message asks the operator to refresh before resubmitting.

The synchronous upload endpoint has no server-side progress stream or cancellation after commit starts. Upload phases are indeterminate. This release does not add delete, account-management, scheduling, or publishing actions to the dashboard.
