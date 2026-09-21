# Implementation Plan: IBOM AI Agent Stack

**Feature Branch**: 001-ibom-ai-agent-stack
**Brief ID**: 001-ibom-ai-agent-stack
**Source brief**: briefs/001-ibom-ai-agent-stack.md
**Hard-coded external brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`
**Constitution version**: 4.7.1
**Constitution SHA-256**: sha256:b8b224cb6377ea80236bc6e9008a82d1341ace05da516d40c18ee8a83a5a4577

## Delivery Ownership

**Owning repository**: aa-ibom-agent-stack
**Affected package/service**: fused Next.js and FastAPI agent stack
**Delivery owner**: Jonathan Bowker

Phase one owns only the fused outer shell. The sibling repos `aa-ibom-pydantic-deepagents` and `aa-ibom-pydantic-ai-backend` are named in the hard-coded brief but are phase-two dependencies.

## Database and Migration Authority

**Schema affected**: No
**Migration repository**: aa-ibom-agent-stack

Phase one keeps the template database behavior and selected pgvector path as shipped. No governed schema migration is introduced by this feature.

## Constitution Check

| Control | Status | Evidence |
|---|---|---|
| Current constitution loaded first | Pass | `.specify/memory/constitution.md` copied from fetched `aa-spec-kit-governance`; lock records version 4.7.1 and SHA-256. |
| Repository boundary | Pass | The hard-coded brief explicitly defines this as a sibling stack outside the standard three client repos. |
| Protected source and reviewable change | Pass | Changes are committed and pushed through git history. |
| Verification before release | Pass | Individual AA governance checks are run for constitution, brief, spec, plan, and tasks. |
| Principle IX model routing | Pass | No phase-two model-routing work is performed in phase one. |
| Principle X milestones and economics | Pass | Phase-one milestone, future phase-two milestones, estimates, and build economics are recorded. |

## Verification Matrix

| Area | Verification |
|---|---|
| Constitution lock | `aa-governance constitution` |
| Brief wrapper | `aa-governance brief briefs/001-ibom-ai-agent-stack.md` |
| Specification | `aa-governance spec specs/001-ibom-ai-agent-stack/spec.md` |
| Implementation plan | `aa-governance plan specs/001-ibom-ai-agent-stack/plan.md` |
| Tasks | `aa-governance tasks specs/001-ibom-ai-agent-stack/tasks.md` |
| Runtime | Start Docker Compose and exercise the phase-one definition-of-done UI path. |

## Complexity Tracking

This plan records a brief-level repository exception rather than a constitutional violation. The governance kit template remains hard-coded for the standard three client repos, so this stack carries an adapted allowed repo list matching the explicit source brief.

No waiver is required for phase one because the stack is not replacing or altering the standard client topology.
