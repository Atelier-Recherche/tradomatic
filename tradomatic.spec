# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

project_root = SPECPATH

datas = [
    ("resources/translations", "resources/translations"),
    ("templates", "templates"),
]

hiddenimports = [
    "src.ui.main_window",
    "src.ui.translation_panel",
    "src.ui.comparison_panel",
    "src.ui.glossary_panel",
    "src.ui.prompts_panel",
    "src.ui.settings_panel",
    "src.core.translator",
    "src.core.project",
    "src.core.glossary",
    "src.core.gemini_api",
    "src.core.claude_api",
    "src.utils.config",
    "src.utils.i18n",
    "src.utils.logger",
    "google.generativeai",
    "anthropic",
    "cryptography",
    "sqlalchemy",
    "markdown",
]

a = Analysis(
    ["src/main.py"],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_paths.py"],
    excludes=[
        "torch", "tensorflow", "transformers", "pandas", "scipy", "sklearn",
        "matplotlib", "notebook", "jupyter", "IPython", "pytest", "cv2",
        "onnxruntime", "yt_dlp", "sympy", "audio_separator",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Tradomatic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
