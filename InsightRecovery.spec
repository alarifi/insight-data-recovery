# -*- mode: python ; coding: utf-8 -*-

# Optimized Spec File for Insight Data Recovery Studio Pro
# Strips unnecessary AI/ML bloat libraries (torch, onnx, scipy, numpy, pandas, etc.)
# Reduces distribution size from ~1.1 GB down to ~120 MB!

excluded_modules = [
    # Heavy AI/ML & Math Frameworks (not used by core recovery engines)
    'torch',
    'torchvision',
    'torchaudio',
    'onnx',
    'onnxruntime',
    'scipy',
    'scipy.libs',
    'numpy',
    'numpy.libs',
    'pandas',
    'pandas.libs',
    'numba',
    'llvmlite',
    'sympy',
    'matplotlib',
    'safetensors',
    'sentencepiece',
    'ml_dtypes',
    'networkx',
    'pydantic',
    'pydantic_core',

    # Heavy Databases & Web / Dev Tools
    'psycopg2',
    'psycopg2_binary.libs',
    'sqlalchemy',
    'cryptography',
    'lxml',
    'yaml',
    'IPython',
    'jupyter',
    'setuptools',
    'distutils',
    'fontTools',
    'tkinter',
    'unittest',
    'test',

    # Unused Qt6 Modules (Recovery Studio is 100% offline desktop QtWidgets)
    'PyQt6.QtNetwork',
    'PyQt6.QtPdf',
    'PyQt6.QtQml',
    'PyQt6.QtQuick',
    'PyQt6.QtSql',
    'PyQt6.QtBluetooth',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtTest',
]

a = Analysis(
    ['InsightDataRecovery\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('InsightDataRecovery\\assets', 'assets'),
        ('InsightDataRecovery\\bin\\ffmpeg.exe', 'bin'),
        ('InsightDataRecovery\\repair', 'repair'),
        ('InsightDataRecovery\\engine', 'engine'),
        ('InsightDataRecovery\\ui', 'ui'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InsightRecovery',
    contents_directory='InsightRecovery',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['InsightDataRecovery\\assets\\app_icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['ffmpeg.exe'],
    name='InsightRecovery',
)
