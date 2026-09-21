# ADR-001: Embeddings Model Choice

**Status**: Accepted for phase two
**Date**: 2026-09-21
**Source brief**: `/Users/jbb/Projects/aa-ibom-stack/ibom-stack-brief.md`

## Context

Phase one keeps the template default embeddings model. Phase two replaces that path so model usage aligns with Advanced Analytica's existing OpenAI relationship and AI Gateway requirement.

## Decision

Use OpenAI `text-embedding-3-small` for text embeddings. Image uploads use a two-step describe-then-embed path: a vision-capable model describes or extracts text from the image, then that text is embedded with `text-embedding-3-small`.

All model calls in this phase-two path must route through the AA AI Gateway.

## Alternatives Considered

Gemini embeddings were rejected for now because they add a second model provider path despite native multimodal embedding support.

Nomic text and vision embeddings were rejected for now because self-hosting adds GPU and inference operations before real usage volume proves the need.

## Consequences

Image embeddings add latency and one additional model step. The path is simpler to govern through the existing OpenAI/Gateway relationship but is less natively multimodal than Gemini or Nomic.

## Reversal Path

If usage volume or quality evidence justifies a change, schedule a later milestone to move to Gemini or Nomic. Switching providers requires re-embedding existing content because vector dimensions and embedding spaces differ.
