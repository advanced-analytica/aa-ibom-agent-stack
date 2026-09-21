# Milestone: 001-ibom-ai-agent-stack

**Feature**: IBOM AI Agent Stack
**Phase**: Phase one - fused template baseline
**Status**: Active
**Source brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`

## Definition Of Done

The phase-one milestone is complete when the fused Vstorm template is running as `aa-ibom-agent-stack` with chat UI, file upload, tool-call cards, live subagent feed, citation panel, plan/task checklist, and completion delivery against the template backend and default embeddings.

## Three-Point Estimate

| Scope | Low | Likely | High |
|---|---:|---:|---:|
| Fork, flatten, configure, verify, and govern phase-one stack | 3h | 7h | 12h |

PERT expected effort: 7.2h.

## Future Milestones

1. Phase two auth: Supabase magic-link.
2. Phase two model routing: AA AI Gateway.
3. Phase two embeddings: OpenAI `text-embedding-3-small` plus image describe-then-embed.
4. Phase two audit and observability: local OTel path, audit facts, DigitalOcean Spaces, Apprise.
5. Phase two agent backend: `pydantic-deepagents` and `pydantic-ai-backend`.
6. Phase two RAG cleanup: remove unused stores and integrations after pgvector is proven.
7. Phase two split: frontend, sandbox backend, and agent framework as separate versioned components.
8. CLI scaffolding: `aa-scaffold new-agent-stack` after phase one is proven.
