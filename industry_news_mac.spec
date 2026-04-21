# industry_news_mac.spec
# PyInstaller build spec for the Industry News macOS application.
#
# Usage (run on a Mac or the GitHub Actions macOS runner):
#   pip install pyinstaller
#   pyinstaller industry_news_mac.spec
#
# Output:
#   dist/IndustryNews.app    <- standard macOS application bundle
#
# After building, wrap it in a DMG for distribution:
#   brew install create-dmg
#   create-dmg \
#     --volname "Industry News" \
#     --window-pos 200 120 \
#     --window-size 600 400 \
#     --icon-size 100 \
#     --icon "IndustryNews.app" 175 190 \
#     --hide-extension "IndustryNews.app" \
#     --app-drop-link 425 185 \
#     "IndustryNews.dmg" \
#     "dist/IndustryNews.app"

from pathlib import Path

ROOT = Path(SPECPATH)   # noqa: F821  (SPECPATH injected by PyInstaller)

block_cipher = None

a = Analysis(
    [str(ROOT / "launch.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Non-Python assets: HTML/CSS/JS frontend and ticker data.
        # server/ and app/ are NOT listed here — PyInstaller bundles
        # them as compiled Python because launch.py imports them
        # directly in the frozen path, letting the analyser follow
        # the full import tree automatically.
        (str(ROOT / "static"), "static"),
        (str(ROOT / "data"),   "data"),
    ],
    hiddenimports=[
        # app.fetch is imported lazily (inside functions in news.py),
        # so the static analyser cannot detect it automatically.
        "app",
        "app.fetch",

        # uvicorn internals loaded dynamically at runtime
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",

        # starlette internals sometimes missed by the analyser
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.base",
        "starlette.staticfiles",

        # other dependencies
        "slowapi",
        "slowapi.errors",
        "feedparser",
        "pydantic",
        "pydantic.deprecated.class_validators",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IndustryNews",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # console=False: no terminal window appears for the user.
    # The app silently starts the server and opens the browser.
    # Errors are written to logs/launch.log inside the .app bundle.
    console=False,
    disable_windowed_traceback=False,
    # argv_emulation handles macOS "open file" and URL events
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,   # replace with "installer/icon.icns" once you have one
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IndustryNews",
)

# BUNDLE wraps the COLLECT output into a proper macOS .app bundle
app = BUNDLE(  # noqa: F821
    coll,
    name="IndustryNews.app",
    icon=None,   # replace with "installer/icon.icns" once you have one
    bundle_identifier="com.industrynews.app",
    version="1.0.0",
    info_plist={
        "CFBundleName":             "Industry News",
        "CFBundleDisplayName":      "Industry News",
        "CFBundleVersion":          "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable":  True,
        "LSBackgroundOnly":         False,
        # Suppress the macOS "app is damaged" false alarm that can
        # occur on some systems when the bundle isn't notarized.
        "LSEnvironment": {
            "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES",
        },
    },
)
