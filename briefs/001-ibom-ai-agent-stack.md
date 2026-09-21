# Build Brief: IBOM AI Agent Stack

**Brief ID**: 001-ibom-ai-agent-stack
**Status**: Approved
**Owner**: Jonathan Bowker
**Approver**: Jonathan Bowker
**Decision**: Approved
**Approved by**: Jonathan Bowker
**Approval date**: 2026-09-21
**Approval evidence**: User-designated hard-coded source brief at `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`.
**Source brief path**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`

## Executive Outcome

Stand up the IBOM AI Agent Stack from the Vstorm full-stack AI agent template as a working phase-one fused template under Advanced Analytica ownership. Phase one must prove the shipped template end to end before any phase-two architectural swaps begin.

## Problem and Current State

Advanced Analytica needs a standalone IBOM agent stack that can later become the proven base for client kit migrations. The source brief fixes the parent folder as `/Users/jbb/Projects/aa-ibom-stack/` and names the outer shell repo `aa-ibom-agent-stack`.

The earlier implementation stood up the fused template but did not create repo-local spec-kit artefacts, which left the phase-one work detached from the spec-driven delivery path required by the constitution.

## Users and Stakeholders

Primary users are Advanced Analytica builders validating the stack locally. Stakeholders are Jonathan Bowker, Advanced Analytica engineering, and future client delivery teams that may inherit this stack once phase two is proven.

## Scope

In scope for phase one:

- Fork and stand up `vstorm-co/full-stack-ai-agent-template` as `aa-ibom-agent-stack`.
- Preserve the shipped template auth, backend wiring, RAG, pgvector path, and default embeddings.
- Keep the flat repo layout expected by the brief, with no nested `generated/` working layer.
- Record the governed brief, spec, plan, tasks, milestone estimate, build economics, and ADR-001 in this repo.

Out of scope for phase one:

- Supabase magic-link auth.
- AI Gateway model routing.
- OpenAI embedding replacement.
- Observability and audit rework.
- Replacing agent framework wiring with `pydantic-deepagents` and `pydantic-ai-backend`.
- Removing unused RAG backends or integrations.
- Splitting the fused template into separate frontend, backend, and agent-framework repos.

## User Journeys and Scenarios

A builder can open the stack in `/Users/jbb/Projects/aa-ibom-stack/aa-ibom-agent-stack`, point their editor at the same folder used by Docker bind mounts, start the template, and exercise chat, upload, tool cards, subagent feed, citations, planning checklist, and completion delivery.

A reviewer can read this brief and the linked spec artefacts to see why phase two work is deliberately deferred until phase-one definition of done is met.

## Functional Outcomes and Business Rules

The stack must run as the Vstorm fused template first. License files and copyright notices from upstream MIT projects must remain intact. `.agents/skills` is the canonical shared skill folder and `.claude/skills` points to it as a symlink; command files remain tool-specific.

## Data and Governance

The selected vector store for the phase-one template path is pgvector. The phase-one implementation must not introduce new governed schema changes in this repo. Constitution version `4.7.1` and preset version `1.5.0` are recorded in `.specify/governance-lock.yml`.

## Security and Access

Phase one keeps upstream auth unchanged and does not add client production access. Secrets must remain in environment files or local runtime configuration, not committed.

## Integrations and Dependencies

Required source repos from the hard-coded brief are:

- `vstorm-co/full-stack-ai-agent-template` to `aa-ibom-agent-stack`.
- `vstorm-co/pydantic-deepagents` to `aa-ibom-pydantic-deepagents`.
- `vstorm-co/pydantic-ai-backend` to `aa-ibom-pydantic-ai-backend`.

The two pydantic repos are phase-two dependencies and are not wired into phase one.

## Operational and Continuity Needs

Docker Compose bind mounts must point at the flat repo root so local edits and container state use the same folder. Restarting containers must not hide work inside an untracked generated subfolder.

## Constraints and Fixed Decisions

The hard-coded brief path is `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`. This stack sits alongside, and does not replace, the standard three-repo client topology of `backend-processing`, `frontend-workspace`, and `supabase-config`.

## Success Measures

Phase one is successful when the fused template runs end to end with chat UI, file upload, tool-call cards, live subagent feed, citation panel, plan/task checklist, and completion delivery using the template backend and default embeddings.

## Assumptions

The user approval captured on 2026-09-21 authorises this repo-local governed brief as the controlled wrapper around the hard-coded external brief.

## Open Questions

None - all material questions resolved.

## Acceptance and Approval

**Decision**: Approved
**Approved by**: Jonathan Bowker
**Approval date**: 2026-09-21
**Approval evidence**: User instructed Codex to use `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md` as the hard-coded brief.
