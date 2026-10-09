# Security Policy

## Reporting a Vulnerability

If you find a security vulnerability in Veridoc, **do not open a public issue**. Please report it privately through GitHub's [Security Advisory feature](https://github.com/themanoj-025/Veridoc/security/advisories) or a private message to the maintainers.

Please include:

- The affected version / commit
- A description of the vulnerability and its impact
- Steps to reproduce (including any minimal exploit)
- Suggested fix, if you have one

## Response

Reports are acknowledged within 5 business days. You will receive an update on the triage and, if accepted, a target date for the fix and disclosure.

## Scope

- Prompt-injection and retrieval-boundary behavior is covered by the red-team suite in `eval/` (see `docs/technical/security-notes.md`).
- Secrets, tokens, and encryption-at-rest handling are in scope for reports.

## Safe Harbor

Research conducted in good faith and reported privately is welcome; we will not pursue legal action for such reports.
