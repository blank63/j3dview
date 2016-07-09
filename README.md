# J3D View
J3D View is a GUI application for viewing and editing Nintendo GameCube/Wii BMD/BDL files.

# Build
**Note:** This section is only relevant if you intend to build the application or run the application from source.

J3D View requires Python 3 with NumPy, PyOpenGL and PyQt5. Building extension modules requires Cython. Building an executable requires PyInstaller.

Building extension modules requires Cython and a C compiler compatible with your Python installation. For Windows see https://matthew-brett.github.io/pydagogue/python_msvc.html to find a compatible compiler. To build the extension modules run the command:
```bash
$ setup.py build_ext --inplace
```
Building an executable requires PyInstaller. To build an executable run the command:
```bash
$ pyinstaller j3dview.spec
```

This has been tested with [CPython 3.5.1 32-bit](https://www.python.org/ftp/python/3.5.1/python-3.5.1.exe), [Visual Studio Community 2015](https://www.visualstudio.com/products/visual-studio-community-vs) (do a custom install and enable C++ support), NumPy 1.11.0, PyOpenGL 3.1.0, PyQt5 5.6, Cython 0.24 and PyInstaller 3.2 (note that there is a [bug](https://github.com/pyinstaller/pyinstaller/pull/1981) int this version) on Windows 8.1 64-bit. 

