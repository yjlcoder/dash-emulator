all:
	python3 setup.py install
	python3 -m dash_emulator.main https://cloud.jace.website/dash360/output.mpd
