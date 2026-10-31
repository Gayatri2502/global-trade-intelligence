# Reviewed public business evidence

`import_public_contacts.py MANIFEST.json --dry-run` validates an evidence manifest without transmitting it. Omit `--dry-run` to ingest into the existing signed cloud discovery queue, which delivers to the Google Sheet's Discovery inbox on reconciliation. Credentials are loaded from the ignored crawler environment file. Imported rows remain unverified; nothing qualifies a lead automatically.

Manifest fields: company, role, product, country, phone, email, website (HTTPS evidence URL), evidence (source, date and limitations), optional lead_id and social_urls. Use NA for missing information. Marketplace catalogue hosts contain multiple businesses: the importer hashes company plus country, rather than merging every seller into the catalogue host. Before importing another batch, compare against the live inbox and existing companies; preserve existing IDs for existing businesses.

The 2026-10-31 research batch contains five IndiaMART-hosted brochures and five company website sources. Direct IndiaMART profile retrieval was unavailable. Catalogue contacts can be outdated or platform-routed; phone reachability, licence IDs and commercial qualifications were not verified. One brochure had conflicting preview and extracted contact fields; disputed fields were excluded and flagged. This is a bounded reviewed batch, not an exhaustive IndiaMART crawl.
