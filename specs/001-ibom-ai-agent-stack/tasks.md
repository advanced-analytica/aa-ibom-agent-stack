# Tasks: IBOM AI Agent Stack

**Brief ID**: 001-ibom-ai-agent-stack
**Source brief**: briefs/001-ibom-ai-agent-stack.md
**Hard-coded external brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`

## Phase One

- [ ] T001 [KEY:001-ibom-ai-agent-stack:aa-ibom-agent-stack:T001] [US1] Validate the phase-one test suite, lint, type check, coverage of at least 80%, secret scan, dependency scan, and Docker runtime smoke path before accepting the fused template baseline.
  - GitHub issue: https://github.com/advanced-analytica/aa-ibom-agent-stack/issues/1
  - Requirements: FR-002, FR-007
  - Constitution controls: I, III, IV, X
  - Validation: `npm test`, `npm run lint`, `npm run type-check`, `pytest`, `detect-secrets`, dependency vulnerability scanning, Docker runtime smoke.
  - Cost estimate: low 1h; likely 2h; high 4h; likely cost GBP 180
  - Completion evidence: Open on issue #1; final runtime and full-suite evidence is not complete in this spec remediation.
- [x] T002 [KEY:001-ibom-ai-agent-stack:aa-ibom-agent-stack:T002] [US1] Implement the flat phase-one repository layout and Docker Compose bind mounts so editor path and container path share `aa-ibom-agent-stack`.
  - GitHub issue: https://github.com/advanced-analytica/aa-ibom-agent-stack/issues/2
  - Requirements: FR-003, FR-004
  - Constitution controls: I, III, IV
  - Validation: `git show --stat 4e396fd` and `docker compose config`.
  - Cost estimate: low 0.5h; likely 1h; high 2h; likely cost GBP 90
  - Completion evidence: Commit `4e396fd` flattened `generated/ibom_ai_agent_stack` into the repo root and updated bind mounts.
- [x] T003 [KEY:001-ibom-ai-agent-stack:aa-ibom-agent-stack:T003] [US3] Create the governed brief, spec, plan, tasks, ADR, milestone, and build-economics artefacts from the hard-coded source brief.
  - GitHub issue: https://github.com/advanced-analytica/aa-ibom-agent-stack/issues/3
  - Requirements: FR-001, FR-008, FR-009, FR-010
  - Constitution controls: III, IV, X
  - Validation: `aa-governance brief`, `aa-governance spec`, `aa-governance plan`, and `aa-governance tasks`.
  - Cost estimate: low 1h; likely 2h; high 3h; likely cost GBP 180
  - Completion evidence: Current commit adds `briefs/001-ibom-ai-agent-stack.md`, `specs/001-ibom-ai-agent-stack/`, `docs/adr/ADR-001-embeddings-model-choice.md`, and `docs/build-economics.md`.
- [x] T004 [KEY:001-ibom-ai-agent-stack:aa-ibom-agent-stack:T004] [US2] Record the phase-two milestones without executing phase-two implementation work.
  - GitHub issue: https://github.com/advanced-analytica/aa-ibom-agent-stack/issues/4
  - Requirements: FR-009
  - Constitution controls: IX, X
  - Validation: Review `specs/001-ibom-ai-agent-stack/milestone.md` and `docs/build-economics.md`.
  - Cost estimate: low 0.5h; likely 1h; high 2h; likely cost GBP 90
  - Completion evidence: Phase-two milestones are documented as deferred in the milestone and economics artefacts.
- [x] T005 [KEY:001-ibom-ai-agent-stack:aa-ibom-agent-stack:T005] [US3] Reconcile governance tasks with GitHub issue reconciliation and phase-one milestone evidence.
  - GitHub issue: https://github.com/advanced-analytica/aa-ibom-agent-stack/issues/5
  - Requirements: FR-008, FR-009, FR-010
  - Constitution controls: III, IV, X
  - Validation: `aa-governance sync-issues specs/001-ibom-ai-agent-stack/tasks.md --apply` once GitHub issue creation is authorised.
  - Cost estimate: low 0.5h; likely 1h; high 2h; likely cost GBP 90
  - Completion evidence: GitHub issue reconciliation created milestone `001-ibom-ai-agent-stack` and issues #1-#5.
