# /usr/bin/env python3
"""
convert the QT UI file to python
QT UI is edited by QT Designer
    * https://doc.qt.io/qt-5/qtdesigner-manual.html
"""
import os

from PyQt5 import uic


def compile_ui(source: str, target: str) -> str:
    """
    compile ui to python
    """
    if not os.access(source, os.R_OK):
        raise SystemExit('can not access ' + source)
    with open(target, encoding='utf-8', mode='w') as fout:
        uic.compileUi(source, fout)
    return open(target, encoding='utf-8').read()


if __name__ == '__main__':
    compile_ui('ui_main.ui', 'ui_main.py')
