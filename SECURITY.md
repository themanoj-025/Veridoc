# Security Policy

## Reporting a Vulnerability

If you discover a security issue in Veridoc, please report it by emailing security@veridoc.dev.

Please do NOT create a public GitHub issue for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Security Measures

- JWT authentication with short-lived tokens
- bcrypt password hashing
- File encryption at rest (Fernet/AES)
- Row-level ownership checks on all data
- Rate limiting per IP
- Prompt injection defense via instruction boundaries
