# Changelog

All notable changes to AegisAI are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Fixed
- `GET /ai-systems` and `GET /documents` return a plain array again by default;
  pass `page`/`limit` to get the `{items, total, page, limit}` envelope.
- `GET /ai-systems` now honours the documented `search`, `risk_level` and
  `compliance_status` filters.
- Document editor saved through the authenticated API client (it previously
  used an unauthenticated `fetch`, so saves returned 401).
- Duplicate rows inside a single CSV bulk import are now rejected.
- Pinned `bcrypt==4.0.1` — passlib 1.7.4 crashes with bcrypt 5.x
  ("password cannot be longer than 72 bytes"), breaking register/login.
- `requirements.txt` installs a working auth stack again.

### Added
- Notifications API: `GET /notifications`, `POST /notifications/read`,
  `DELETE /notifications/{id}` plus the `create_notification` helper.
- Document templates for data governance, transparency notice, human oversight
  plan and incident report (previously returned 400 "No template available").
- Guard scan responses now include the sanitized prompt when the decision is
  `sanitize`.
- `GET /badge/{system_id}` — public SVG/JSON compliance badge.
- `GET /analytics/summary` and `GET /analytics/compliance-timeline`.
- Analytics and Notifications pages in the frontend are wired to the API, and
  all pages (analytics, notifications, onboarding) have routes.
- `Download PDF` button in the Documents page.
- A blocked Guard scan now raises a `guard_block` notification.
- Frontend login fetches the profile with the freshly issued token, so signing
  in no longer redirects straight back to the login screen.

---

## [0.1.0] — 2026-04-05

### Added
- **Compliance Engine** — EU AI Act risk classification (Minimal / Limited / High / Unacceptable)
- AI system registry with CRUD endpoints
- Compliance document generation (Technical Documentation, Risk Assessment, Conformity Declaration)
- JWT authentication (register, login, `/me`)
- **LLM Guard module** — 4-layer prompt injection defence:
  - Regex heuristic filter
  - DeBERTa-v3 intent classifier (benign / suspicious / malicious)
  - Decision engine (allow / sanitize / block)
  - Prompt sanitizer (LOW / MEDIUM / HIGH levels)
- `POST /api/v1/guard/scan` endpoint
- **RAG Intelligence module** — FAISS vector store + LangChain 0.2 retrieval chain
- `POST /api/v1/rag/query` endpoint
- Provider-agnostic LLM client (OpenAI-compatible: works with Ollama, Groq, Together AI, vLLM …)
- React 18 + TypeScript frontend (Dashboard, AI Systems, Classification, Documents)
- Docker Compose setup
- Kubernetes deployment & HPA configs
- Colab-ready notebook for fine-tuning the Guard classifier

### Known Limitations (good first contributions!)
- RAG knowledge base is empty by default — needs regulatory documents ingested
- No audit log for Guard decisions yet
- Stripe billing wired up but not activated
- Frontend pages for Guard and RAG not yet built
