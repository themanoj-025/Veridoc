# Contributing to Veridoc

Thanks for your interest in Veridoc! Bug reports, documentation, and pull requests are welcome.

## Getting started

1. Fork the repository and clone your fork.
2. Create a feature branch: `git checkout -b feature/amazing`.
3. Backend: `cd backend && pip install -r requirements.txt`
4. Frontend: `cd frontend && npm install`

## Development workflow

- Add or update tests for every change.
- Backend tests: `cd backend && pytest`
- Frontend tests: `cd frontend && npm test`
- Verify both apps boot: `uvicorn app.main:app --reload` (backend) and `npm run dev` (frontend).
- Follow the existing patterns: service layer with DI container, Pydantic schemas, structured logging.

## Security

Review [SECURITY.md](SECURITY.md) before reporting vulnerabilities.

## Commit conventions

Keep commits small and focused. Prefix messages with a type, e.g. `feat:`, `fix:`, `docs:`, `test:`.

## Opening a pull request

1. Push your branch and open a PR against `main`.
2. Describe what you changed and why.
3. Link any related issue.

By contributing, you agree that your contributions are licensed under the MIT License.
