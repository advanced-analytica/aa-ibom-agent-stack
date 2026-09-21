# Build Economics: IBOM AI Agent Stack

**Source brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`
**Feature**: 001-ibom-ai-agent-stack

## Phase One

| Work | Low | Likely | High | Likely cost |
|---|---:|---:|---:|---:|
| Fork and stand up fused template baseline | 2h | 4h | 8h | GBP 360 |
| Flatten repo layout and Docker bind mounts | 0.5h | 1h | 2h | GBP 90 |
| Add governed spec, plan, task, ADR, and economics artefacts | 1h | 2h | 3h | GBP 180 |
| Runtime and governance verification | 1h | 2h | 4h | GBP 180 |

Likely phase-one total: 9h, GBP 810.

## Phase Two Milestones

| Milestone | Low | Likely | High | Notes |
|---|---:|---:|---:|---|
| Supabase magic-link auth | 4h | 8h | 16h | Replace template auth only after phase one is proven. |
| AA AI Gateway routing | 6h | 12h | 24h | Remove direct provider calls. |
| OpenAI embeddings and image describe-then-embed | 4h | 8h | 16h | Implements ADR-001. |
| Audit and observability rework | 8h | 16h | 32h | OTel, audit facts, DO Spaces, Apprise. |
| Pydantic deepagents/backend wiring | 12h | 24h | 48h | Replace four unused template frameworks. |
| RAG and integration cleanup | 4h | 8h | 16h | Remove unused stores after pgvector is proven. |
| Three-component split | 16h | 32h | 64h | Split only after fused reference works. |
| CLI scaffolding | 8h | 16h | 32h | Add `aa-scaffold new-agent-stack` after phase one. |

These estimates are planning entries and must be refreshed when each milestone is opened.
