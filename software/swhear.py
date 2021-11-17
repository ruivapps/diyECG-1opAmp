"""
The core SWHEar class for continuously monitoring microphone data.

The Ear class is the primary method used to access microphone data.
It has extra routines to audomatically detec/test sound card, channel,
and rate combinations to maximize likelyhood of finding one that
works on your system (all without requiring user input!)

Although this was designed to be a package, it's easy enough to work
as an entirely standalone python script. Just drop this .py file in
your project and import it by its filename. Done!
"""

import logging
import threading
import time

import numpy as np
import pyaudio

logger = logging.getLogger()

'''
def FFT(data, rate):
    """given some data points and a rate, return [freq,power]"""
    data = data*np.hamming(len(data))
    fft = np.fft.fft(data)
    fft = 10*np.log10(np.abs(fft))
    freq = np.fft.fftfreq(len(fft), 1/rate)
    return freq[:int(len(freq)/2)], fft[:int(len(fft)/2)]
'''


class Ear:
    def __init__(self, device=None, rate=None, chunk=4096, maxMemorySec=5):
        """
        Prime the Ear class to access audio data. Recording won't start
        until stream_start() is called.
        - if device is none, will use first valid input (not system default)
        - if a rate isn't specified, the lowest usable rate will be used.
        """

        # configuration
        self.chunk = chunk  # doesn't have to be a power of 2
        self.maxMemorySec = maxMemorySec  # delete if more than this around
        self.device = device
        self.rate = rate

        # internal variables
        self.chunksRecorded = 0
        self.p = pyaudio.PyAudio()  # keep this forever
        self.audio = self.p
        self.t = False  # later will become threads
        self.running = False  # boolean show the state of the capture stream
        self.keepRecording = None
        self.data = None
        self.msg = None
        self.stream = None

        self.mics = []
        self._get_mics()

    # SOUND CARD TESTING

    def _get_mics(self) -> list:
        """ get all available mics we can use (write)
        """
        for idx in range(self.p.get_device_count()):
            if self._verify_device(idx):
                self.mics.append(self.audio.get_device_info_by_index(idx))
        if not self.mics:
            logger.error('no valid micphone found')
        return self.mics

    def _verify_device(self, device_idx: int, rate: int = None) -> bool:
        """ verify the device is writable
        """
        device = self.audio.get_device_info_by_index(device_idx)
        logger.debug(device)
        if device.get('maxInputChannels', 0) < 1:
            return False
        rate = rate or int(device.get('defaultSampleRate', -1))

        try:
            self.audio.open(
                format=pyaudio.paInt16, channels=1, input_device_index=device_idx, frames_per_buffer=self.chunk, rate=rate, input=True)
            logger.info('found mic: %s index: %s',
                        device.get('name'), device_idx)
        except OSError:
            logger.warning(
                'can not open device %s [%s] for write', device_idx, device.get('name'))
            return False
        return True

    def _lowest_sample_rate(self, device_idx: int) -> int:
        """
        # FIXME: not sure why the lowest sample rate is required
        """
        device = self.audio.get_device_info_by_index(device_idx)
        rates = [8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100,
                 48000, 88200, 96000, 192000, int(device.get('defaultSampleRate', -1))]
        for rate in rates:
            if self._verify_device(device_idx, rate=rate):
                return rate
        logger.error(
            'can not find valid sample rate for device: %s [%s]', device_idx, device.get('name'))
        return 0

    # SETUP AND SHUTDOWN

    def close(self):
        """gently detach from things."""
        if not self.running:
            return
        self._stream_stop()
        print(" -- sending stream termination command...")
        self.keepRecording = False  # the threads should self-close
        if self.t:
            while self.t.is_alive():
                time.sleep(.1)  # wait for all threads to close
            self.stream.stop_stream()
        self.p.terminate()
        self.running = False

    # LIVE AUDIO STREAM HANDLING

    def _stream_readchunk(self):
        """reads some audio and re-launches itself"""
        while self.keepRecording:
            data = np.fromstring(self.stream.read(self.chunk), dtype=np.int16)
            self.data = np.concatenate((self.data, data))
            self.chunksRecorded += 1
            dataFirstI = self.chunksRecorded*self.chunk-len(self.data)
            if len(self.data) > self.maxMemorySec*self.rate:
                pDump = len(self.data)-self.maxMemorySec*self.rate
                #print(" -- too much data in memory! dumping %d points."%pDump)
                self.data = self.data[pDump:]
                dataFirstI += pDump
            time.sleep(1/self.rate)
        self.stream.close()
        self.p.terminate()
        self.keepRecording = None
        print(" -- stream STOPPED")

    def stream_start(self, device_idx: int) -> None:
        """adds data to self.data until termination signal"""

        self.running = True
        self.rate = self.rate or self._lowest_sample_rate(device_idx)
        logger.debug('start stream with rate: %s', self.rate)
        device_name = self.audio.get_device_info_by_index(
            device_idx).get('name')

        self.msg = f'recording from "{device_name}"  (device {device_idx}) at {self.rate} Hz'
        print(self.msg)

        self.data = np.array([])

        print(" -- starting stream")
        self.keepRecording = True  # set this to False later to terminate stream
        self.stream = self.audio.open(
            input_device_index=device_idx, format=pyaudio.paInt16, channels=1,
            rate=self.rate, input=True, frames_per_buffer=self.chunk)
        self.t = threading.Thread(target=self._stream_readchunk)
        self.t.start()

    def _stream_stop(self, waitForIt=True):
        """send the termination command and (optionally) hang till its done"""
        print('stoppping the stream')
        self.keepRecording = False
        if waitForIt is False:
            return
        while self.keepRecording is not None:
            time.sleep(.1)

    # WAV FILE AUDIO

    '''
    # DATA RETRIEVAL
    def getPCMandFFT(self):
        """returns [data,fft,sec,hz] from current memory buffer."""
        if not len(self.data):
            return
        data = np.array(self.data)  # make a copy in case processing is slow
        sec = np.arange(len(data))/self.rate
        hz, fft = FFT(data, self.rate)
        return data, fft, sec, hz
    '''

    @staticmethod
    def softEdges(data, fracEdge=.05):
        """multiple edges by a ramp of a certain percentage."""
        rampSize = int(len(data)*fracEdge)
        mult = np.ones(len(data))
        window = np.hanning(rampSize*2)
        mult[:rampSize] = window[:rampSize]
        mult[-rampSize:] = window[-rampSize:]
        return data*mult

    def getFiltered(self, freqHighCutoff=50):
        if freqHighCutoff <= 0:
            return self.data
        fft = np.fft.fft(self.softEdges(self.data))  # todo: filter needed?
        trim = len(fft)/self.rate*freqHighCutoff
        fft[int(trim):-int(trim)] = 0
        return np.real(np.fft.ifft(fft))


if __name__ == "__main__":
    print("This script is intended to be imported, not run directly!")
