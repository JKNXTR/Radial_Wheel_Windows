# Radial Wheel

A Windows radial quick-access menu (Python 3.9+ / PySide6). Press a global hotkey and an 8-sector wheel appears at the cursor.

- Sectors: keyboard shortcuts, folders, Windows commands, favorites, sound, internet, wheel settings, programs
- Dynamic slots, grid/size configurator, tile colors with transparency
- Tray icon, autostart, no console window, GUI installer (`install.bat`)
- Update from a .zip archive (Settings -> Update)
- 20 languages (English by default, Bulgarian included); the language is changed in Settings -> Functions and applies after a restart. Texts missing from a translation fall back to English.

Install: run `install.bat`. Uninstall: `uninstall.bat`. Tests: `python tools/smoke_test.py`.
