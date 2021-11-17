# DIY ECG (with 1 op-amp)

forked from https://github.com/swharden/diyECG-1opAmp

## Changes

* add UI allow user to select input devices.
* add UI with start/stop button.
* update to python 3.9 + QT5

## run

only tested on MacOS. the pyaudio requires **portaudio** installed (via port or brew)

```bash
cd software
python3 -m pip install -r requirement.txt
python3 main.py
```

## dev

download QT Designer to work with ui_main.ui

## todo

soem interesting things possible in the future.

basic

	* record the wave and reply wave file.
	* export the graph (length)
	* persistent settings

need some learning

	* calculate heart rate
	* smoother display
	* pattern recognition
		- sinus rhythm
		- arrhythmias

build

	* raspberry PI build with 5" screen
		- boot into to app
		- hardware button replace keyboard/mouse
		- battery powered
