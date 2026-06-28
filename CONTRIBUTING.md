# Contributing to RepoPilot

First off, thank you for considering contributing to RepoPilot. It's people like you that make RepoPilot such a great tool.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/InfoSage05/repopilot.git
   cd repopilot
   ```

2. **Install with development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

## Testing

We use `pytest` for unit testing. To run the tests:

```bash
pytest tests/ -v
```

## Linting & Type Checking

Code quality is enforced using `ruff` and `mypy`. Ensure your code passes before committing:

```bash
ruff check . && mypy app/
```

## Branch Naming Convention

Please follow these conventions when creating branches:

- `feat/...` for new features
- `fix/...` for bug fixes
- `docs/...` for documentation updates

## PR Checklist

- [ ] I have read the `CONTRIBUTING.md` file.
- [ ] My code passes all tests (`pytest tests/ -v`).
- [ ] My code passes linting (`ruff check . && mypy app/`).
- [ ] I have updated the documentation accordingly.
- [ ] I have added tests for new features or bug fixes.
