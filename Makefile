install:
	pip3 install requests requests-oauthlib
	install -C spotify-terminal.py3 /usr/local/bin/spotify-terminal

uninstall:
	rm -f /usr/local/bin/spotify-terminal
