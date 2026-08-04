# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Fixed

- Allow keyless custom providers through `provider list`, `check`, and `analyze`.
- Probe Anthropic's models endpoint and require HTTP 200 for a successful check.
- Reset provider defaults atomically when changing provider type and honor an
  Anthropic base URL override for both checks and analysis.
- Return structured errors for invalid images, malformed provider responses,
  and invalid configuration files.
- Omit Ollama's JSON response format for free-form prompts.

### Added

- Input file-size, pixel-count, and decompression-bomb limits.
- Local keyless custom-provider CLI integration coverage.
- Cross-platform Python 3.11/3.13 CI and the MIT license text.
- Versioned cloud image-transmission consent in first-install scripts, with a
  default-deny prompt before the virtual environment is created.
- Correct global-rule targets for Cursor, Claude Code, and custom Codex homes,
  plus approval-gated cross-platform install and removal instructions.
