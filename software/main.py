"""
diyECG GUI for monitoring live ECG through sound card input (by Scott Harden).
If you haven't built the circuit, test this software by playing demo_ecg.wav
while you run this software. If you don't use a virtual audio cable to connect
the output (speaker jack) to the input (default microphone jack), consider
running an actual cable to connect these two.
"""

import logging
import sys
import time
import webbrowser

import numpy as np
import pyqtgraph
import pyqtgraph.exporters
from PyQt5 import QtCore, QtWidgets

import swhear
import ui_main

logger = logging.getLogger()


class ExampleApp(QtWidgets.QMainWindow, ui_main.Ui_MainWindow):
    def __init__(self, parent=None):
        pyqtgraph.setConfigOption('background', 'w')  # before loading widget
        super(ExampleApp, self).__init__(parent)
        self.setupUi(self)
        self.grECG.plotItem.showGrid(True, True, 0.7)
        self.btnSave.clicked.connect(self.saveFig)
        self.btnSite.clicked.connect(self.website)
        self.btnStart.clicked.connect(self.start_capture)
        self.btnStop.clicked.connect(self.stop_capture)
        self.btnPause.clicked.connect(self.pause_state)
        self.btnPause.setEnabled(False)

        stamp = "DIY ECG by Scott Harden"
        self.stamp = pyqtgraph.TextItem(stamp, anchor=(-.01, 1), color=(150, 150, 150),
                                        fill=pyqtgraph.mkBrush('w'))
        self.ear = swhear.Ear(chunk=int(100))  # determines refresh rate
        self.boxMic.addItems([device['name'] for device in self.ear.mics])
        self.stop = False

    def pause_state(self) -> None:
        """
        disable start,stop during pause
        """
        state = True
        if self.btnPause.isChecked():
            state = False
        self.btnStart.setEnabled(state)
        self.btnStop.setEnabled(state)

    def start_capture(self) -> None:
        """
        start to capture from the Mic
        """
        self.ear = swhear.Ear(chunk=int(100))  # determines refresh rate
        logger.debug('trying to start capture')
        print('picked mic index: ', self.boxMic.currentIndex())
        print('picked mic name: ', self.boxMic.currentText())
        if not self.ear.mics:
            logger.error('no available mic, can not start the capture')
            return
        self.stop = False
        self.ear.stream_start(
            self.ear.mics[self.boxMic.currentIndex()]['index'])
        self.lblDevice.setText(self.ear.msg)
        self.update()
        self.btnPause.setEnabled(True)
        self.boxMic.setEnabled(False)
        print('capture started')

    def stop_capture(self) -> None:
        """
        stop capture from the Mic
        """
        self.btnStart.setEnabled(False)
        self.btnPause.setEnabled(False)
        logger.debug('trying to stop capture')
        self.stop = True
        self.boxMic.setEnabled(True)
        self.btnStart.setEnabled(True)
        print('capture stopped')

    def closeEvent(self, event):
        self.ear.close()
        event.accept()

    def saveFig(self):
        fname = "ECG_%d.png" % time.time()
        exp = pyqtgraph.exporters.ImageExporter(self.grECG.plotItem)
        exp.parameters()['width'] = 1000
        exp.export(fname)
        print("saved", fname)

    def update(self):
        t1, timeTook = time.time(), 0
        if len(self.ear.data) and not self.btnPause.isChecked():
            freqHighCutoff = 0
            if self.spinLowpass.value() > 0:
                freqHighCutoff = self.spinLowpass.value()
            data = self.ear.getFiltered(freqHighCutoff)
            if self.chkInvert.isChecked():
                data = np.negative(data)
            if self.chkAutoscale.isChecked():
                self.Yscale = np.max(np.abs(data))*1.1
            self.grECG.plotItem.setRange(xRange=[0, self.ear.maxMemorySec],
                                         yRange=[-self.Yscale, self.Yscale], padding=0)
            self.grECG.plot(np.arange(len(data))/float(self.ear.rate), data, clear=True,
                            pen=pyqtgraph.mkPen(color='r'), antialias=True)
            self.grECG.plotItem.setTitle(
                self.lineTitle.text(), color=(0, 0, 0))
            self.stamp.setPos(0, -self.Yscale)
            self.grECG.plotItem.addItem(self.stamp)
            timeTook = (time.time()-t1)*1000
            # print("plotting took %.02f ms"%(timeTook))
        if not self.stop:
            msTillUpdate = int(self.ear.chunk/self.ear.rate*1000)-timeTook
            QtCore.QTimer.singleShot(int(max(0, msTillUpdate)), self.update)
        else:
            self.ear.close()
            self.grECG.clear()

    def website(self):
        webbrowser.open("http://www.SWHarden.com")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = ExampleApp()
    form.show()
    app.exec_()
