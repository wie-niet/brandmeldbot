#!/usr/bin/env python3

# matrix chatbot
from chatbot import Chatbot
import configparser
import sys

#
# Main:
#
if __name__ == '__main__':
	
	
	# read config
	config = configparser.ConfigParser()
	
	try:
		with open('config.ini') as f:
			config.read_file(f)

	except FileNotFoundError as e:
		print("Warning: No config.ini found! Copy all other settings out of config-default.ini.")
		config.add_section('matrix-conf')

		
	# get config
	bot_conf = config['matrix-conf']
		
	
	
	print("Login for generating matrix token config.")
	host     = input("Enter host [{}]: ".format(bot_conf.get('host'))) or bot_conf.get('host', fallback='https://matrix.org')
	
	username = bot_conf.get('username', fallback=bot_conf.get('userid'))
	username = input("Enter username [{}]: ".format(username)) or username
	
	password = input("Enter password [{}]: ".format(bot_conf.get('password'))) or bot_conf.get('password')
	room     = input("Enter room [{}]".format( bot_conf.get('room'))) or bot_conf.get('room')
	

	# # chat login
	# print({'host':host,
	# 	'username':username,
	# 	'password':password,
	# 	'room':room})

	bot = Chatbot(
		host=host,
		username=username,
		password=password, 
		room=room)

	# make sure token is preserve
	bot.logout_on_exit = False

	# get token
	token = bot.client.api.token
	user_id = bot.client.user_id
	
	print("""
#
# Element Matrix bot config (created with '{}')
#
[matrix-conf]
host    = {}
userid = {}
token   = {}
room    = {}
""".format(sys.argv[0], host, user_id, token, room))