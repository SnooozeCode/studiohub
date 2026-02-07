# SnooozeCo Studio Hub

A professional desktop application for managing print studio workflows, including poster printing, mockup generation, file tracking, and consumables management.

## Version

v0.10.1-beta (Refactored Architecture)

## Features

- **Dashboard** - Real-time metrics, paper and ink tracking, print statistics
- **Print Manager** - Queue management, Photoshop integration, batch printing
- **Mockup Generator** - Template-based mockup creation with backgrounds
- **Missing Files Tracker** - File availability scanning and reports
- **Print Jobs Log** - Complete print history and tracking
- **Settings Management** - Path configuration, theme selection, preferences
- **Production Costs** - Cost tracking and analysis

## Architecture Improvements

This version has been refactored from a monolithic 1,757-line file into a clean, modular architecture:

- **Dependency Injection** - Centralized dependency management
- **Service Layer** - Clear separation of concerns
- **Testable Components** - Each module can be tested independently
- **Better Maintainability** - Easy to find and modify code

### Directory Structure

```
app/
├── main.py                          # Application entry point
├── constants.py                     # Application constants
├── config_manager.py                # Configuration management
├── hub/                             # Core application
│   ├── main_window.py              # Main window (400 lines vs 1,757)
│   └── dependency_container.py     # Dependency injection
├── ui/
│   ├── widgets/                     # Reusable widgets
│   ├── sidebar/                     # Sidebar components
│   └── ...
├── services/
│   ├── navigation/                  # Navigation service
│   ├── index/                       # Index management
│   ├── lifecycle/                   # Startup and view initialization
│   └── ...
├── hub_models/                      # Data models
├── hub_views/                       # UI views
└── theme/                           # Theming system
```

## Requirements

- Python 3.11+
- PySide6
- psutil

See `requirements.txt` for full dependencies.

## Installation

1. Install Python 3.11 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## First-Time Setup

On first launch, you'll be prompted to configure:

- Photoshop executable path
- Patents root directory
- Studio root directory
- Runtime root directory
- Print jobs folder
- JSX scripts folder

These can be configured later in Settings.

## Configuration

Configuration is stored in:
- Windows: `%APPDATA%/SnooozeCo/StudioHub/config.json`
- Other: `~/.SnooozeCo/StudioHub/config.json`

## Themes

Two themes available:
- **Dracula** - Dark theme (default)
- **Alucard** - Light theme

Toggle with the theme button in the sidebar.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .
```

## Changelog

### v0.10.1-beta (Refactored)

**Major Refactoring:**
- Broke down monolithic hub.py (1,757 lines) into modular architecture
- Created dependency injection container
- Extracted navigation, index management, and lifecycle services
- Improved testability and maintainability
- Added comprehensive documentation

**Technical Improvements:**
- Centralized constants and configuration
- Better error handling and logging
- Cleaner signal wiring
- Improved type hints throughout

## License

Proprietary - SnooozeCo

## Support

For issues or questions, contact SnooozeCo support.
