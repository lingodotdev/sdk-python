# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of the Lingo.dev Python SDK
- Support for text localization
- Support for object localization
- Support for chat sequence localization
- Support for HTML document localization
- Support for batch text localization to multiple locales
- Language detection functionality
- User authentication checking with `whoami()`
- Progress tracking for long-running operations
- Comprehensive test suite
- Type hints and Pydantic validation
- GitHub Actions for CI/CD and automated publishing
- Fast mode for improved performance on larger batches
- Reference translation support for consistency
- Automatic payload chunking for large datasets
- Error handling for various API scenarios

### Features
- **Text Localization**: Translate individual text strings
- **Object Localization**: Translate Python dictionaries with string values
- **Chat Localization**: Translate chat conversations while preserving speaker names
- **HTML Localization**: Translate HTML documents while preserving structure
- **Batch Processing**: Translate text to multiple target languages in one call
- **Language Detection**: Automatically detect the language of input text
- **Progress Callbacks**: Track progress for long-running operations
- **Fast Mode**: Enable faster processing for larger batches
- **Reference Translations**: Provide reference translations for consistency
- **Chunking**: Automatic handling of large payloads through intelligent chunking
- **Type Safety**: Full type hints and runtime validation with Pydantic
- **Comprehensive Testing**: Unit tests, integration tests, and mocked tests
- **CI/CD**: Automated testing and publishing workflows

### Technical Details
- **Python Support**: Python 3.8+
- **Dependencies**: requests, pydantic, beautifulsoup4, nanoid
- **API Compatibility**: Compatible with Lingo.dev API v1
- **Error Handling**: Comprehensive error handling with appropriate exception types
- **Documentation**: Extensive documentation with examples and API reference

## [0.1.0] - 2024-01-XX

### Added
- Initial release