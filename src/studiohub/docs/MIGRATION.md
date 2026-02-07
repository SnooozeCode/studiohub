# Migration Guide: Original → Refactored

## Overview

This guide helps you transition from the original `hub.py` to the refactored architecture.

## What Changed

### Files Removed
- `hub.py` (1,757 lines) - **REPLACED**

### Files Added

**New Core Files:**
- `main.py` - Application entry point
- `constants.py` - Application constants
- `hub/main_window.py` - Refactored main window (400 lines)
- `hub/dependency_container.py` - Dependency injection

**New Services:**
- `services/navigation/navigation_service.py` - Navigation management
- `services/index/index_manager.py` - Index lifecycle
- `services/lifecycle/startup_manager.py` - Startup validation
- `services/lifecycle/view_initializer.py` - View setup

**New Widgets:**
- `ui/widgets/placeholder_view.py`
- `ui/widgets/click_catcher.py`
- `ui/widgets/notifications_drawer.py`

### Files Unchanged

All existing modules remain unchanged:
- `config_manager.py` ✓
- `hub_models/` ✓
- `hub_views/` ✓
- `services/` (existing files) ✓
- `theme/` ✓
- `ui/` (existing files) ✓
- `assets/` ✓
- `scripts/` ✓

## How to Migrate

### Step 1: Backup

```bash
# Backup your current application
cp -r your_app your_app_backup
```

### Step 2: Replace Files

1. **Delete** the old `hub.py`
2. **Copy** all new files from `refactored_app/` to your application directory

### Step 3: Verify Structure

Your directory should look like:

```
your_app/
├── main.py                    # NEW
├── constants.py               # NEW
├── config_manager.py          # EXISTING
├── requirements.txt           # NEW
├── README.md                  # NEW
├── hub/                       # NEW DIRECTORY
│   ├── __init__.py
│   ├── main_window.py
│   └── dependency_container.py
├── services/
│   ├── navigation/            # NEW
│   ├── index/                 # NEW
│   ├── lifecycle/             # NEW
│   └── ...                    # EXISTING
├── ui/
│   ├── widgets/               # NEW
│   └── ...                    # EXISTING
└── ...                        # EXISTING
```

### Step 4: Update Launch Method

**Old way:**
```bash
python hub.py
```

**New way:**
```bash
python main.py
```

### Step 5: Test

1. **Launch the application:**
   ```bash
   python main.py
   ```

2. **Verify features:**
   - Dashboard loads
   - Navigation works
   - Theme toggle works
   - Settings can be accessed
   - Index refreshes

3. **Check for errors** in the console

## Configuration

Your existing configuration will work without changes!

Configuration location remains the same:
- `%APPDATA%/SnooozeCo/StudioHub/config.json` (Windows)

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'hub'`

**Solution:** Make sure you're running from the application root directory:
```bash
cd your_app
python main.py
```

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'PySide6'`

**Solution:** Install requirements:
```bash
pip install -r requirements.txt
```

### Path Issues

**Problem:** Application can't find files

**Solution:** Check that all existing modules (`hub_models`, `hub_views`, `services`, etc.) are present

## Code Changes for Extensions

If you've modified the original `hub.py`, here's how to port your changes:

### Adding a New View

**Old way (hub.py):**
```python
def _init_views(self):
    self.view_my_new_view = MyNewViewQt(parent=self.stack)
    self.views["my_new_view"] = self.view_my_new_view
```

**New way (services/lifecycle/view_initializer.py):**
```python
def create_views(self):
    # ... existing code ...
    
    view_my_new = MyNewViewQt(parent=self._parent)
    
    self._views = {
        # ... existing views ...
        "my_new_view": view_my_new,
    }
```

### Adding Signal Wiring

**Old way (hub.py):**
```python
def _wire_signals(self):
    self.my_model.data_changed.connect(self.my_view.refresh)
```

**New way (services/lifecycle/view_initializer.py):**
```python
def wire_signals(self):
    # ... existing code ...
    self._wire_my_custom_signals()

def _wire_my_custom_signals(self):
    view = self._views["my_view"]
    model = self._deps.my_model
    model.data_changed.connect(view.refresh)
```

### Adding Navigation Hooks

**Old way (hub.py):**
```python
def show_view(self, key):
    if key == "my_view":
        self._prime_my_view()
```

**New way (hub/main_window.py):**
```python
def _register_navigation_hooks(self):
    # ... existing code ...
    nav.register_activation_hook("my_view", self._on_my_view_activated)

def _on_my_view_activated(self):
    # Prime the view
    pass
```

## Benefits of New Architecture

1. **Testability** - Each component can be tested independently
2. **Maintainability** - Easy to find and modify code
3. **Scalability** - Simple to add new features
4. **Readability** - Clear separation of concerns
5. **Debugging** - Easier to trace issues

## Rollback Plan

If you need to rollback:

1. Restore from backup:
   ```bash
   cp -r your_app_backup/* your_app/
   ```

2. Run the old way:
   ```bash
   python hub.py
   ```

## Getting Help

1. Check the README.md for common issues
2. Review the refactoring_plan.md for architecture details
3. Contact development team

## Validation Checklist

- [ ] Application launches without errors
- [ ] Dashboard displays correctly
- [ ] All navigation items work
- [ ] Theme toggle functions
- [ ] Settings can be modified
- [ ] Index refresh works
- [ ] Print manager loads
- [ ] Existing configuration preserved
- [ ] No feature regressions

## Timeline

Recommended migration timeline:
- **Day 1:** Backup and copy new files
- **Day 2:** Test thoroughly
- **Day 3:** Deploy to production

## Notes

- Your existing configuration and data are **not affected**
- All features work identically to before
- Performance should be the same or better
- File paths and dependencies are unchanged
