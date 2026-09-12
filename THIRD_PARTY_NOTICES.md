# Third-party components

Usage Garden is an independent utility, not an official OpenAI product.

- **OpenAI Codex 0.154.0**: Copyright OpenAI. Apache License 2.0. Official, unmodified Windows binary included in packaged builds, with upstream LICENSE and NOTICE in `vendor/`. Source: https://github.com/openai/codex/tree/rust-v0.154.0. The build script verifies the release archive against its published SHA-256 digest.
- **PySide6 / Qt for Python 6.8.3 and Qt**: Copyright The Qt Company and contributors. Distributed under applicable LGPL v3 / GPL and third-party licenses. Dynamically linked libraries remain replaceable in `_internal/`; applicable distribution license files are included under `licenses/`. Sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://download.qt.io/archive/qt/6.8/6.8.3/single/. Users may replace or debug modified LGPL-covered libraries as permitted by their licenses.
- **Python 3.12**: Copyright Python Software Foundation. PSF license; runtime packaged by PyInstaller. Source and license: https://www.python.org/downloads/source/ and https://docs.python.org/3/license.html.
- **PyInstaller 6.12.0**: GPL with its bootloader exception permitting distribution of bundled applications. https://pyinstaller.org/en/stable/license.html.

All flower illustrations are original, resolution-independent Qt drawing code in `usage_garden/art.py`; no external images or fonts are required. Georgia and Segoe UI are requested from the operating system, not redistributed.
