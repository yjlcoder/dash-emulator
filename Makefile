all:
	python3 setup.py install
	python3 -m dash_emulator.main http://192.168.1.101/www/static/live.mpd
