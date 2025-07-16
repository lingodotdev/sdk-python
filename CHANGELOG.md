# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of the Lingo.dev Python SDK
- Text localization with `localize_text()`
- Object localization with `localize_object()`
- Chat sequence localization with `localize_chat()`
- Batch text localization with `batch_localize_text()`
- Language detection with `recognize_locale()`
- User authentication checking with `whoami()`
- Progress tracking for long-running operations
- Fast mode for improved performance on larger batches
- Reference translation support for consistency
- Automatic payload chunking for large datasets
- Comprehensive error handling
- Type hints and Pydantic validation
- Comprehensive test suite with 93% coverage
- GitHub Actions for CI/CD and automated publishing

### Technical Details
- **Python Support**: Python 3.8+
- **Dependencies**: requests, pydantic, nanoid
- **API Compatibility**: Compatible with Lingo.dev API v1
- **Error Handling**: Comprehensive exception handling with appropriate types
- **Documentation**: Extensive documentation with examples and API reference

## [0.1.0] - 2024-01-XX

### Added
- Initial release
