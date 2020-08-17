#!/usr/bin/env python3

import sys
import logging
import traceback
import argparse
import numpy
import OpenGL
from PyQt5 import QtCore, QtWidgets, QtGui


def configure_logging(logfile):
    if logfile is None:
        logging.basicConfig(level=logging.WARNING)
        return

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)

    file_handler = logging.StreamHandler(logfile)
    file_handler.setLevel(logging.DEBUG)

    logging.basicConfig(level=logging.DEBUG, handlers=[stderr_handler, file_handler])


def configure_gl():
    OpenGL.ERROR_ON_COPY = True
    OpenGL.STORE_POINTERS = False
    OpenGL.FORWARD_COMPATIBLE_ONLY = True


def configure_qt():
    QtWidgets.QApplication.setOrganizationName('BlankSoft')
    QtWidgets.QApplication.setApplicationName('J3D View')
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

    surface_format = QtGui.QSurfaceFormat()
    surface_format.setRenderableType(QtGui.QSurfaceFormat.OpenGL)
    surface_format.setVersion(3, 3)
    surface_format.setProfile(QtGui.QSurfaceFormat.CoreProfile)
    surface_format.setSamples(4)
    QtGui.QSurfaceFormat.setDefaultFormat(surface_format)


def excepthook(*exception_info):
    try:
        # Close the main window to prevent more exceptions being thrown
        main_window.close()
    except NameError:
        pass

    logging.critical('unexpected error', exc_info=exception_info)
    logging.shutdown()

    message = QtWidgets.QMessageBox(None)
    message.setWindowTitle(QtWidgets.qApp.applicationName())
    message.setIcon(QtWidgets.QMessageBox.Critical)
    message.setText('An unexpected error occurred.')
    message.setDetailedText(''.join(traceback.format_exception(*exception_info)))
    message.setStandardButtons(QtWidgets.QMessageBox.Ok)
    message.setDefaultButton(QtWidgets.QMessageBox.Ok)
    message.exec_()

    QtWidgets.qApp.exit()
    sys.exit()


parser = argparse.ArgumentParser(description='View Nintendo GameCube/Wii BMD/BDL files')
parser.add_argument('file_name', nargs='?', metavar='FILE', help='file to view')
parser.add_argument('--logfile', type=argparse.FileType('w'), metavar='LOGFILE', help='write log to %(metavar)s')
arguments = parser.parse_args()

configure_logging(arguments.logfile)
configure_gl()
configure_qt()

logging.info('Python version: %s', sys.version)
logging.info('NumPy version: %s', numpy.version.version)
logging.info('PyOpenGL version: %s', OpenGL.__version__)
logging.info('Qt version: %s', QtCore.QT_VERSION_STR)
logging.info('PyQt version: %s', QtCore.PYQT_VERSION_STR)

# This implicitly imports OpenGL.GL. Logging and OpenGL have to have been
# configured before this happens.
from widgets.editor import Editor

application = QtWidgets.QApplication(sys.argv)

sys.excepthook = excepthook

main_window = Editor()
main_window.show()

if arguments.file_name is not None:
    main_window.openFile(arguments.file_name)

application.exec_()

