# Chatbot for NSC Solution F2 Fire control unit 
Push messagesfrom NSC Solution F2 Fire control unit's serialline RS-232 printer interface to an Element.io/matrix chatroom.


## Install
### clone files into /opt/brandmeldbot
	cd /opt && git clone https://github.com/wie-niet/brandmeldbot.git


### python modules
	python3 -m pip install matrix_client
	python3 -m pip install pyserial

### systemd service
Edit if needed, make sure the path and user are set correctly.

	install -m 644 systemd.brandmeldbot.service /etc/systemd/system/brandmeldbot.service
	systemctl daemon-reload
	systemctl enable brandmeldbot


