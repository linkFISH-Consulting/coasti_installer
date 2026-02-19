# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

TLDR:
- Bugfixes 0.0.1 (Revision)
- Features 0.1.0 (Minor Version)
- Breaking Changes 1.0.0 (Major Version)


## 0.1.5 - 2026-02-19

### Fixed

- Product install would crash on windows when using git auth token

## 0.1.4 - 2026-02-17

### Fixed

- Fixed tests when running from main branch.
- Now using platformdirs to determine template cache dir.

## 0.1.3

### Added
- Now wrapping [copier](https://copier.readthedocs.io/en/stable/) for all template
  and content-installation logic
- Can now manage git authentication flows via auth token or ssh keypair
- Docker Dev container
- UV project for dependency management
- Github action for automatic testing

