# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Zpx, please report it responsibly.

**Please do NOT open a public issue for security vulnerabilities.**

### How to Report

- **Preferred:** Open a [private security advisory](https://github.com/M-2000-0/ZPX/security/advisories/new) on GitHub.
- **Alternative:** Email the maintainers with a detailed description.

Include as much of the following as possible:

1. A minimal, reproducible test case
2. The Zpx and Python versions affected
3. Expected vs. actual behavior
4. Any impact assessment (if known)

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Disclosure Timeline

- We will acknowledge reports within 5 business days.
- We aim to triage within 10 business days.
- Fixes are released as soon as practical; public disclosure happens after a fix is available.

## Security Considerations

Zpx is an interpreted language. Like any runtime, untrusted code should be run in a sandbox. The `zpx run` and `zpx ai` commands can execute filesystem, network, and database operations — only execute Zpx programs from sources you trust.
