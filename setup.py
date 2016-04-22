#!/usr/bin/env python3

try:
    from cx_Freeze import setup,Executable
    has_cx_freeze = True
except ImportError:
    from distutils.core import setup
    has_cx_freeze = False
    print('Could not import cx_Freeze. Building executable not possible.')

import platform
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy

arguments = dict(
        name='J3D View',
        version='0.3',
        description='Nintendo GameCube/Wii BMD/BDL file viewer',
        scripts = ['j3dview.py'],
        py_modules=['gl','viewer_widget','explorer_widget','forms'],
        packages=['btypes','gx','j3d'])

arguments['ext_modules'] = cythonize(Extension(
    'gx.texture',
    ['gx/texture.pyx'],
    include_dirs=[numpy.get_include()]))

if has_cx_freeze:
    base = 'Win32GUI' if platform.system() == 'Windows' else None
    build_exe = dict(
            includes=['viewer_widget','explorer_widget','forms'],
            packages=['OpenGL.platform','OpenGL.arrays'],
            include_files=[('ui/Editor.ui','ui/Editor.ui'),('ui/ViewSettingsForm.ui','ui/ViewSettingsForm.ui'),('ui/TextureForm.ui','ui/TextureForm.ui')])
    arguments['executables'] = [Executable('j3dview.py',base=base)]
    arguments['options'] = dict(build_exe=build_exe)

setup(**arguments)

