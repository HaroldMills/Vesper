# -*- mode: python -*-

# PyInstaller spec file for the Vesper Recorder.

block_cipher = None


a = Analysis(['vesper_recorder.py'],
             pathex=['C:\\Users\\Harold\\Documents\\Code\\Python\\Vesper\\vesper\\scripts'],
             binaries=[],
             datas=[('Vesper Recorder Config.yaml', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='vesper_recorder',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='vesper_recorder')
