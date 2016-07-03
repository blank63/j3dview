# -*- mode: python -*-

block_cipher = None

ui_files = ('widgets/*.ui','widgets')

excludes = [
        'bz2',
        'lzma',
        'select',
        'socket',
        'ssl',
        'numpy.distutils', # Needs to be excluded for socket and select to be excluded
        'PyQt5.QtPrintSupport']

analysis = Analysis(
        ['j3dview.py'],
        binaries=None,
        datas=[ui_files],
        hiddenimports=[],
        hookspath=[],
        runtime_hooks=[],
        excludes=excludes,
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher)

pyz = PYZ(
        analysis.pure,
        analysis.zipped_data,
        cipher=block_cipher)

exe = EXE(
        pyz,
        analysis.scripts,
        exclude_binaries=True,
        name='j3dview',
        debug=True,
        strip=False,
        upx=True,
        console=True)

collect = COLLECT(
        exe,
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        strip=False,
        upx=True,
        name='j3dview')
