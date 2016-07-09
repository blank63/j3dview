#!/usr/bin/env python3

from setuptools import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy

texture = Extension(
        'gx.texture',
        ['gx/texture.pyx'],
        include_dirs=[numpy.get_include()])

setup(
        name='J3D View',
        version='0.4',
        description='Nintendo GameCube/Wii BMD/BDL file viewer and editor',
        url="https://github.com/blank63/j3dview/",
        license="MIT",
        scripts = ['j3dview.py'],
        py_modules=['gl','qt'],
        packages=['btypes','gx','j3d','widgets'],
        package_data={'widgets':['*.ui']},
        ext_modules=cythonize(texture),
        install_requires=['numpy','PyOpenGL','PyQt5'])

