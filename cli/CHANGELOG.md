# Changelog

All notable changes to the Bonito CLI will be documented in this file.

## [0.2.0] — 2026-02-18

### Added
- **Knowledge Base (RAG) commands** — full `bonito kb` command group:
  - `bonito kb list` — list all knowledge bases
  - `bonito kb create` — create a new knowledge base (upload, S3, Azure Blob, GCS)
  - `bonito kb info KB_ID` — show KB details + stats
  - `bonito kb upload KB_ID FILE...` — upload documents (PDF, DOCX, TXT, MD, HTML, CSV, JSON)
  - `bonito kb documents KB_ID` — list documents in a KB
  - `bonito kb search KB_ID "query"` — semantic vector search with relevance scoring
  - `bonito kb delete KB_ID` — delete a knowledge base
  - `bonito kb delete-doc KB_ID DOC_ID` — delete a single document
  - `bonito kb sync KB_ID` — trigger cloud storage sync
  - `bonito kb sync-status KB_ID` — check sync progress
  - `bonito kb stats KB_ID` — detailed statistics
- **Deployment commands** documented in CLI spec (were implemented in 0.1.0 but not spec'd)

### Changed
- User-Agent header now dynamically uses package version
- Updated CLI spec with complete command reference including deployments and KB commands

### Fixed
- `__main__.py` now correctly calls `app()` instead of `main()`
- API endpoint reference updated to reflect actual backend routes


## [0.1.0] — 2026-02-15

### Added
- Initial CLI release
- `bonito auth` — login/logout/whoami/status
- `bonito providers` — list/status/add (AWS/Azure/GCP)/test/remove
- `bonito models` — list/search/info/enable/sync
- `bonito chat` — interactive chat, one-shot, compare mode, pipe input, /slash commands
- `bonito gateway` — status/usage/logs/keys/config management
- `bonito policies` — routing policy CRUD + test + stats
- `bonito analytics` — overview/usage/costs/trends/digest
- `bonito deployments` — list/create/status/delete
- Rich terminal output with tables, panels, and colored status indicators
- `--json` flag on all commands for CI/CD automation
- 🐟 ASCII fish art banner
