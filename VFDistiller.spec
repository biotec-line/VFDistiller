# -*- mode: python ; coding: utf-8 -*-
import os

BASE = SPECPATH

a = Analysis(
    [os.path.join(BASE, 'Variant_Fusion_pro_V17.py')],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(BASE, 'locales', 'translations.json'), 'locales'),
        (os.path.join(BASE, 'ICO', 'ICO.ico'), 'ICO'),
        (os.path.join(BASE, 'data', 'annotations', 'GRCh37.gtf.gz'), os.path.join('data', 'annotations')),
        (os.path.join(BASE, 'data', 'annotations', 'GRCh38.gtf.gz'), os.path.join('data', 'annotations')),
        (os.path.join(BASE, 'variant_fusion_settings.json.example'), '.'),
        (os.path.join(BASE, 'translator.py'), '.'),
        (os.path.join(BASE, 'translator_patch.py'), '.'),
        (os.path.join(BASE, 'lightdb_index_worker.py'), '.'),
    ],
    hiddenimports=[
        'scipy.stats',
        'scipy.special',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Nicht benoetigte Pakete die PyInstaller sonst mitschleppt
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'keras',
        'pandas', 'pyarrow',
        'matplotlib', 'mpl_toolkits',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'black', 'pylint', 'astroid',
        'jedi', 'parso',
        'sympy', 'numba', 'llvmlite',
        'sqlalchemy', 'alembic',
        'pygments',
        'lxml',
        'pygame',
        'onnxruntime',
        'fsspec',
        'pywin32', 'win32com', 'pythoncom', 'pywintypes',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VFDistiller',
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
    icon=[os.path.join(BASE, 'ICO', 'ICO.ico')],
)
