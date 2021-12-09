# Element.io/matrix chat-bot for NSC Solution F2 Brandmeld centrale 
Push serial line messages form NSC Solution F2 Brandmeld centrale to an Element.io/matrix chat room.


## Install
### clone files into /opt/brandmeldbot
cd /opt && git clone https://github.com/wie-niet/brandmeldbot.git


### python modules
	python3 -m pip install matrix_client
	python3 -m pip install pyserial

### systemd service
edit if needed, make sure the path and user are set correctly.
	install -m 644 systemd.brandmeldbot.service /etc/systemd/system/systemd.brandmeldbot.service
	systemctl daemon-reload
	systemctl enable brandmeldbot


