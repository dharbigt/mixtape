# Contributing

Thanks for helping improve Mixtape.

## Ground Rules

- Keep changes focused and small.
- Do not commit uploaded audio files, artwork, credentials, or database files.

## Development Setup

See [README.md](README.md) for environment setup.

## Suggested Workflow

1. Create a branch from `main`.
2. Make your change with tests or verification notes.
3. Run a local sanity check:

```bash
python -m compileall app
```

4. Update docs when behavior changes.
5. Open a pull request with a clear summary.

## Pull Request Checklist

- [ ] Change is scoped and documented.
- [ ] No secrets, uploaded media, or database files committed.
- [ ] M3U generation and track metadata extraction remain correct.

## Reporting Bugs

Please include:

- expected behavior
- actual behavior
- reproduction steps
- route/URL used
- relevant logs (redacted)
