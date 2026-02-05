# Claude Code Project Instructions

## Git Workflow

This project uses **Git Flow**. Follow these guidelines for all git operations:

### Branch Structure
- `main` — Production releases only (never commit directly)
- `develop` — Integration branch for completed features
- `feature/*` — Feature branches (create from and merge to `develop`)
- `hotfix/*` — Urgent production fixes (merge to both `main` and `develop`)
- `release/*` — Release preparation (merge to both `main` and `develop`)

### Key Rules
1. **Feature branches merge to `develop`**, not `main`
2. **PRs target `develop`** unless it's a hotfix
3. **Never push directly to `main`** — only release merges
4. Use `--no-ff` merges to preserve branch history

### Common Operations

**Starting work on a feature:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/feature-name
```

**Completing a feature (merge to develop):**
```bash
git checkout develop
git merge --no-ff feature/feature-name
git push origin develop
```

**Creating a PR:**
- Always target `develop` branch
- Use descriptive PR titles

## Development Notes

- Always read relevant files before making changes
- Run tests after making modifications: `pytest tests/python/ -v`
- Follow existing code style (C: LLVM style, Python: PEP 8)
- The C backend is in `Backend/src/`, Python frontend in `python-backend/`
