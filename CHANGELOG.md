# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2024-01-03

### Changed

- Updated dependencies (Flask, Flask-Babel)
- Fixed missing `ip_in_passlist` in dummy
- Using kwargs for filter calls
- Logging requests to all endpoints for easier debugging (all in DEBUG)

## [1.2.0] - 2023-12-22

### Removed

- Removed `ALWAYS_ONLINE`: always assume routing

### Changed

- IP must be in passlist to be considered registered

## [1.1.0] - 2023-09-08

### Added

- Spanish translation

## [1.0.1] - 2023-05-08

### Changed

- Upgraded dependencies (Flask, Flask-Babel, peewee)

## [1.0.0] - 2022-11-05

- Initial version
