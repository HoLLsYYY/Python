from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root/'source/bear.py')], pathex=[str(root/'source')],
             binaries=[], datas=[(str(root/'assets'),'assets')],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=[], noarchive=False, optimize=0)
# Qt uses the Windows ICU API. Do not bundle unrelated ICU DLLs from PATH.
a.binaries = [item for item in a.binaries if Path(item[0]).name.lower() not in ('icuuc.dll','icudt78.dll')]
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='Bear',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,
          console=False,disable_windowed_traceback=False,
          icon=str(root/'assets/bear.ico'))

