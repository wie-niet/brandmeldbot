#!/usr/bin/env python3


import configparser
import logging

import signal # support ctrl-c 

# matrix chatbot
from chatbot import Chatbot
# brandmeld-installatie 
import brandmelder

logger = logging.getLogger(__name__)

#
# handle CTRL-C / stop signal
#

def signal_handler_stop(sig, frame):
	global signal_handler_stop_count
	global signal_handler_stop_callbacks
	global signal_handler_stop_callbacks_last
	
	logger.info('stopping by {} (ctrl-c/systemd stop/..) ({})'.format(str(signal.Signals(sig)), signal_handler_stop_count))
	# CTRL-C hit count, set signal_handler_stop_count: to number of tries or -1.
	if signal_handler_stop_count == 0:
		# we are not wanted here anymore: let's erase our selfs
		signal.signal(sig,signal.SIG_DFL)
		# end try signal_handler_stop_callbacks_last
		signal_handler_stop_callbacks = signal_handler_stop_callbacks_last
		
	elif signal_handler_stop_count > 0: 
		# let's count down
		signal_handler_stop_count = signal_handler_stop_count - 1	
	

	# stop main services:
	while (len(signal_handler_stop_callbacks) != 0):
		callback = signal_handler_stop_callbacks.pop()
		logger.info('# signal_handler_stop_callbacks[ {} ]; exec: {} '.format(len(signal_handler_stop_callbacks), callback))
		callback()
	
# global for self restart.
SELF_RESTART = False		

# catch sig -HUP
def signal_handler_reload(sig, frame):
	global SELF_RESTART
	# set global variable
	SELF_RESTART = True
	logger.info('SIG HUP: (shutdown and) restart ourself ')
	signal_handler_stop(sig, frame)
	# import sys, os
	# print ("RESTART: ", sys.argv[0], sys.argv, "(+ENV)" )
	# os.execve(sys.argv[0], sys.argv, os.environ)
	# quit()
	




#
# Main:
#
if __name__ == '__main__':
	# register CTRL-C / CTRL-D 
	signal.signal(signal.SIGINT, signal_handler_stop)
	signal_handler_stop_count = 1 # set to -1 for infinite
	signal_handler_stop_callbacks = [] # callback function for exit.
	signal_handler_stop_callbacks_last = []  # callback function for final exit.
	signal.signal(signal.SIGTERM, signal_handler_stop)
	signal.signal(signal.SIGHUP, signal_handler_reload)

	
	# read config
	config = configparser.ConfigParser()
	with open('config.ini') as f:
		config.read_file(f)

	# set log output for stderr, get loglevel from config
	logging.basicConfig(level=logging.getLevelName(config.get('main', 'loglevel', fallback = 'info').upper()))
	
	# 
	# brandmeld-installatie message parser
	#
	bmi = brandmelder.LogReader()

	# add exit callback: bmi.exit()
	signal_handler_stop_callbacks.append(bmi.exit_graceful)
	signal_handler_stop_callbacks_last.append(bmi.exit)
	

	#

	#
	# Matrix Elelement chat bot
	#
	bot_conf = config['matrix-conf']
	bot = Chatbot(bot_conf.get('host'), bot_conf.get('user'), bot_conf.get('pass'), bot_conf.get('room'))

	# add exit callback: bot.logout()
	# signal_handler_stop_callbacks_last.append(bot.logout)

	# print startup text:
	startup_text = config.get('main','startup_text', fallback=None)
	if startup_text is not None:
		bot.talk(startup_text)
		
	# print startup html:
	startup_html = config.get('main','startup_html', fallback=None)
	if startup_html is not None:
		bot.room.send_html(startup_html)
	
	# serial conf:
	serial_conf = {	'port': config.get('serial','port'), 
					'baudrate': config.getint('serial','baudrate', fallback=-1), # use -1 for None
					'timeout': config.getint('serial','timeout', fallback=1),
					'encoding': config.get('serial','encoding', fallback=None)}

	#			
	# Main loop: get messages from serial input 
	#
	for message in bmi.serial_reader(serial_conf):
		# send message over chat
		# bot.talk(message)
		bot.talk(message, 'text')
		# bot.talk_html(message.to_html())
	
	# end of Main loop, exit when needed..
	
	
	# print shutdown text:
	shutdown_text = config.get('main','shutdown_text', fallback=None)
	if shutdown_text is not None:
		bot.talk(shutdown_text)
		
	# print shutdown html:
	shutdown_html = config.get('main','shutdown_html', fallback=None)
	if shutdown_html is not None:
		bot.room.send_html(shutdown_html)

	# matrix exit:
	bot.logout()
	
	# serial close.
	bmi.exit() # probably not needed, but no harm to do twice
	

	# in case of SIGHUP:
	if SELF_RESTART:
		import sys, os
		logger.info('SELF_RESTART : {} {}'.format(str(sys.argv[0]), str(sys.argv)))
		os.execve(sys.argv[0], sys.argv, os.environ)
		quit()

# vim: set noet ts=4 sw=4:
