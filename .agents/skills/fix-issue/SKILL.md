---
name: fix-issue
description: Investigate and fix a backend or full-stack issue in this project. Use when asked to debug, reproduce, root-cause, patch, test, and summarize a defect.
---

# Fix Issue

Fix the issue described by the user.

1. **Understand** - search the codebase for relevant code, read the files, understand current behavior
2. **Reproduce** - if possible, identify a test case or request that triggers the issue
3. **Root cause** - trace through Routes -> Services -> Repositories to find where the bug originates
4. **Fix** - implement the fix following project conventions:
   - Domain exceptions in services (not HTTP errors)
   - `db.flush()` in repositories (not `commit`)
   - Type hints on all changed signatures
5. **Test** - run `cd backend && uv run pytest` to verify no regressions
6. **Lint** - run `cd backend && uv run ruff check . --fix && uv run ruff format .`
7. **Summary** - explain what was changed and why
