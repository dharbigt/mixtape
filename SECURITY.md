# Security Policy

## Supported Versions

Security updates are provided for the latest `main` branch.

## Reporting a Vulnerability

Please report vulnerabilities privately to maintainers. Do not open a public issue for sensitive reports.

Include:

- affected route/feature
- reproduction steps
- impact assessment
- any logs or traces (redacted)

## Scope Notes

Common risk areas in this project:

- authentication/session handling (Google OAuth, Flask-Login)
- file upload validation (audio files, artwork)
- path traversal in track/artwork file handling
- private media exposure
