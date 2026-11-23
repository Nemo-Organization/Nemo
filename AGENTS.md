# Nemo implementation context

Guardian's agreed delivery pack starts at `docs/guardian/README.md`. Read the product requirements, architecture, data model and OpenAPI contract before implementing a task. The ordered plan is `docs/superpowers/plans/2026-11-23-guardian.md`; task prompts are in `docs/guardian/agent-prompts.md`.

- Keep `Frontend/` and `Backend/` casing and the existing frontend feature structure. `Frontend/AGENTS.md` contains additional Next.js instructions.
- Frontend work reuses current styling tokens, components and i18n namespaces. Use paired English/Vietnamese locale keys and strict namespace generation.
- Backend is a proposed Python FastAPI modular monolith using PostgreSQL. SQLAlchemy models and versioned Alembic migrations must agree with `docs/guardian/schema.sql`.
- Treat OpenAPI field names/enums and documented state transitions as shared agreements. Update related docs and callers together when an implementation requires a change.
- Resolve actor permissions and sandbox ownership on the server. AI proposes evidence. Server code enforces restrictions, reservations and money writes.
- Use PostgreSQL for meaningful concurrency tests. Run the checks for the assigned task and report actual results.
- The `leads`, `endpoints` and `logs` frontend examples are scaffold features. Their mock business concepts do not define Guardian.
- Follow the repository's existing branch policy. A local implementation task does not authorize pushing, merging or deploying externally without the user's instruction.
