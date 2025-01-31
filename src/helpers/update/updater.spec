# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['updater_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MEAUpdater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Matches --windowed in workflow
    disable_windowed_traceback=False,
    target_arch=None,  
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MEAUpdater',
)

app = BUNDLE(
    coll,
    name='MEAUpdater.app',
    icon=None,
    bundle_identifier='com.booka66.meaupdater',
    info_plist={
        'LSUIElement': True,
        'NSAppleEventsUsageDescription': 'This app needs to modify applications.',
        'NSSystemAdministrationUsageDescription': 'This app needs to modify applications.',
    },
)
