# Bonito Roadmap

## Scaling TODOs

### Database Migrations
- **Current:** Migrations run in entrypoint.sh (single instance, fine for now)
- **At scale:** Move to a dedicated pre-deploy step when running multiple containers. Concurrent migration attempts from multiple workers can corrupt the DB. Options:
  - Railway pre-deploy hook (if supported)
  - CI/CD pipeline step (run migration job before rolling deploy)
  - Kubernetes init container (runs once before pods start)

### Code Review Snapshots
- Run Alembic migration for `code_review_snapshots` table
- Test end-to-end snapshot extraction on live PRs
- Add syntax highlighting to public snapshot viewer

### Bonito Battles
- Adversarial agent debates (inspired by AgentRnD /versus)
- Showcase feature, backlog
