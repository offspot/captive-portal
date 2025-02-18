# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2025-02-18

### Changed

- Updated Kiwix Hotspot logo
- Updated favicon
- Expecting `HOTSPOT_NAME` to be a self-sufficient name. Not suffixed anymore with `'s Hotspot` in captive portal UI

## [1.4.0] - 2024-04-18

### Changed

- Changed registration endpoint from `/register` to `/register-hotspot` to avoid collisions.

## [1.3.0] - 2024-02-09

### Added

- `CAPTURED_ADDRESS` env defaulting to `198.51.100.1` to identify traffic that must be captured
- CAPTIVE_PASSLIST chain now starts with return rule for captured-address so it always ends up in portal

### Changed

- Allow host rule in CAPTIVE_PASSLIST is added AFTER the captured address rules

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
