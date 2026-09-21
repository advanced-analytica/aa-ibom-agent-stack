# Feature Specification: IBOM AI Agent Stack

**Feature Branch**: 001-ibom-ai-agent-stack
**Created**: 2026-09-21
**Status**: Active
**Brief ID**: 001-ibom-ai-agent-stack
**Source brief**: briefs/001-ibom-ai-agent-stack.md
**Hard-coded external brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`

## User Scenarios & Testing

### User Story 1 - Phase-one fused template works as shipped

As an AA builder, I need the Vstorm full-stack template running as the `aa-ibom-agent-stack` fused repo so I can prove the baseline before any constitutional rework begins.

**Acceptance Scenarios**:

1. Given the stack is started locally, when a user opens the frontend, then the chat UI loads against the template backend.
2. Given a user uploads a supported file, when the backend processes it, then upload handling, citation display, and completion delivery remain functional.
3. Given the agent invokes tools or subagents, when the UI receives events, then tool-call cards, live subagent feed, and plan/task checklist render.

### User Story 2 - Phase two is constrained until phase one is done

As a reviewer, I need phase-two work recorded but not executed in phase one so the build does not wander into auth, model-routing, embedding, audit, framework, RAG cleanup, or repo-split work prematurely.

**Acceptance Scenarios**:

1. Given the spec is reviewed, when phase-two milestones are inspected, then each is separately named and deferred.
2. Given the implementation is inspected, when direct phase-two swaps are considered, then they are absent from phase one unless explicitly scheduled.

### User Story 3 - Governance artefacts exist beside the code

As an AA maintainer, I need the brief, spec, plan, tasks, ADR, and build economics in the repo so future work can be validated against the constitution rather than reconstructed from chat context.

**Acceptance Scenarios**:

1. Given the repository is checked out, when `.specify`, `briefs`, `specs`, and `docs/adr` are inspected, then phase-one governance artefacts exist.
2. Given the AA validator is run, when constitution, brief, spec, plan, and tasks are checked, then they pass their individual gates.

## Requirements

### Functional Requirements

- **FR-001**: The repo must treat `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md` as the hard-coded source brief for this feature.
- **FR-002**: Phase one must stand up `vstorm-co/full-stack-ai-agent-template` as `aa-ibom-agent-stack` without replacing its auth, backend wiring, RAG, observability, or default embeddings.
- **FR-003**: The working tree must use the flat repo root `aa-ibom-agent-stack` rather than a nested `generated/ibom_ai_agent_stack` layer.
- **FR-004**: Docker Compose bind mounts must point to the same flat folder that the editor opens.
- **FR-005**: `.agents/skills` must remain the canonical shared skill source, with `.claude/skills` symlinked to it.
- **FR-006**: Claude commands and Codex/custom prompt commands must remain separate because their command formats differ.
- **FR-007**: Upstream MIT license files and copyright notices must remain intact.
- **FR-008**: The repo must include ADR-001 for the phase-two embeddings model decision.
- **FR-009**: Phase two must be represented as seven separate future milestones.
- **FR-010**: CLI scaffolding via `aa-scaffold new-agent-stack` must remain a future milestone after phase one is proven.

## Governance and Risk Impact

The stack is a sibling forked stack outside the standard three client product repos. This exception is authorised by the hard-coded source brief and recorded in `.specify/aa-governance.yml`.

Main risks are premature phase-two changes, license drift, hidden generated directories, missing bind mounts, and untracked spec work. Controls are the repo-local brief/spec/plan/tasks, ADR, build economics entry, and constitution lock.

## Success Criteria

- **SC-001**: Phase-one runtime demonstrates chat, file upload, tool-call cards, live subagent feed, citation panel, plan/task checklist, and completion delivery.
- **SC-002**: No phase-two replacement work is merged before phase-one definition of done is met.
- **SC-003**: The governed artefacts identify the hard-coded source brief and constitution version.
- **SC-004**: Individual governance validation passes for constitution, brief, spec, plan, and tasks.
