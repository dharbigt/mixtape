# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Release checklist

- [ ] Verify `SECRET_KEY` is configured in deployment.
- [ ] Confirm no uploaded tracks, artwork, or database files are included in release artifacts.
- [ ] Run CI and ensure all checks pass.
- [ ] Update version tag and release notes.

### Added

- Mixtape management with track upload and M3U playlist generation.
- Google OAuth authentication via authlib.
- Audio metadata extraction from MP3, M4A, and AAC files using mutagen.
- Drag-and-drop track upload with embedded artwork extraction.
- Public mixtape directory with M3U download links.
- Admin dashboard for mixtape and track management.
