# Repository Guidelines

## Project Structure & Module Organization

This repository is currently a small assignment workspace rather than an application. The root contains:

- `Flexiple Engineering Hiring - Candidate Assignment.pdf`, the assignment brief.
- `profiles.json - Flexiple Engineering Challenge sample data`, the sample candidate/profile data.
- `README.md`, the project overview and usage notes.
- `requirements.txt`, the reserved Python dependency manifest.
- `.venv/`, a local Python virtual environment; do not commit generated environment files.

If implementation is added, keep production code in a clearly named package or `src/` directory, tests in `tests/`, and static fixtures/assets in `data/` or `assets/`. Keep reusable modules separate from one-off analysis scripts.

## Build, Test, and Development Commands

No build, test, or run commands are configured yet. For Python work, create and activate a local environment before installing dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

When tooling is introduced, document its canonical commands in `README.md` and here (for example, `pytest` for tests and `python -m <package>` for local execution).

## Coding Style & Naming Conventions

Use Python 3 conventions, four-space indentation, descriptive `snake_case` names for modules, functions, and variables, and `PascalCase` for classes. Prefer small, typed functions and clear JSON schemas. Add a formatter/linter such as Ruff or Black only when the project adopts a consistent configuration; run it before submitting changes.

## Testing Guidelines

There is no test suite or coverage requirement yet. Use `pytest` when tests are added, place them under `tests/`, and name files `test_<module>.py` with functions such as `test_filters_profiles_by_skill`. Include edge cases for malformed, missing, and empty profile data.

## Commit & Pull Request Guidelines

The existing history contains a single concise commit (`first commit with empty README`), so use short imperative subjects (for example, `Add profile matching prototype`). Pull requests should explain the behavior change, identify relevant data or assignment requirements, list validation commands and results, and include screenshots or sample output for user-facing changes. Keep unrelated refactors separate.

## Security & Configuration Tips

Treat candidate/profile data as potentially sensitive. Do not add credentials, production records, or personal data to the repository. Keep secrets in environment variables, and update `.gitignore` before generating local outputs or caches.
