# Contributing to Veridoc

## Development Setup

```bash
cp .env.example .env
docker compose up --build -d
```

## Code Style

- **Python**: Follow PEP 8, use type hints, max line length 100
- **TypeScript**: Use strict mode, follow project tsconfig
- **Commit messages**: Use conventional commits (feat:, fix:, docs:, etc.)

## Pull Request Process

1. Ensure all tests pass
2. Update docs if adding features
3. Add evaluation data if modifying retrieval pipeline
