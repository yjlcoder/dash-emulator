all:
	python3 setup.py install
	python3 -m dash_emulator.main http://cloud.jace.website/static/live.mpd
