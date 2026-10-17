# Contributing

## Development setup

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

The project uses Black for formatting, Ruff for linting, and pytest for tests.
Run the same checks as CI before opening a pull request:

```bash
black src tests experiments scripts
ruff check src tests experiments scripts
python -m pytest -q
```

## Code changes

- Keep simulation behavior deterministic for a fixed seed.
- Put reusable simulation behavior under `src/mosaic_comm`.
- Put campaign orchestration and plotting under `experiments/`.
- Keep generated results, figures, and LLM caches out of commits.
- Add a focused regression test when changing a shared simulator contract.
- Preserve existing scheme names unless a migration path is documented.
- Describe policies by their behavior; document module, ID, and result-key changes together.
- Retain copyright notices and record source attribution in `NOTICE.md`.
- Use `MICA` for the framework in prose and figures, `mica` in policy IDs, and `Mica` in class names.

Use short comments for non-obvious algorithmic choices. Public classes and
functions should have docstrings that describe inputs, outputs, and side effects.
