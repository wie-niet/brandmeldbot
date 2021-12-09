
# element.io SDK
from matrix_client.client import MatrixClient, MatrixRequestError
from enum import Enum

import matrix_client.client

import logging
logger = logging.getLogger(__name__)

# ###
# # usage:
#
# from chatbot import Chatbot
# bot = Chatbot(bot_conf.get('host'), bot_conf.get('user'), bot_conf.get('pass'), bot_conf.get('room'))
# bot.talk("Hello World")
# bot.logout()
#
# ###


# more info https://matrix-org.github.io/matrix-python-sdk/matrix_client.html

class MessageType(Enum):
	NOTICE = 'notice'
	TEXT = 'text'
	HTML = 'html'

class Chatbot:
	"""Simplified Matrix Chatbot"""

	
	def __init__(self, host, user, passw, room):
		# connect with server
		self.client = MatrixClient(host)
		logger.info("bot connected with host: {}".format(host))
		logger.info("matrix_client.client.ENCRYPTION_SUPPORT: {}".format(matrix_client.client.ENCRYPTION_SUPPORT))
		

		# login user
		try:
			self.client.login(user, passw)
		except MatrixRequestError as e:
			print("MatrixRequestError:", e)
			if e.code == 403:
				logger.info("Bad username or password.")
				# sys.exit(4)
			else:
				logger.info("Check your sever details are correct.")
				# sys.exit(2)			
			raise(e) 
			
		except MissingSchema as e:
			logger.info("Bad URL format.")
			print("DEBUG:", e)
			# sys.exit(3)
			raise(e)

		logger.info("bot connected as user: {}".format(user))
	


		# join chat room
		try:
			self.room = self.client.join_room(room)
		except MatrixRequestError as e:
			print("MatrixRequestError:", e)
			if e.code == 400:
				logger.info("Room ID/Alias in the wrong format")
				# sys.exit(11)
			else:
				logger.info("Couldn't find room.")
				# sys.exit(12)
			raise(e)
		logger.info("bot connected to room: {}".format(room))

	# 	#room callback:
	# 	# self.room.add_listener(lambda room, event : print("CALLBACK room.add_listener => room, event:", room, event, "\n", self.print_event(event)))
	# 	self.client.add_listener(lambda event : print("CALLBACK client.add_listener => event:", event, "\n", self.print_event(event)))
	#
	# 	# Parameters:	callback (func(room_id, state) – Callback called when an invite arrives
	# 	self.client.add_invite_listener(lambda room_id, state: print("CALLBACK add_invite_listener => room_id, state:", room_id, state, "\n"))
	# 	self.client.start_listener_thread()
	#
	#
	# def print_event(self,event):
	# 	print("debug: type(event)", type(event))
	# 	print("debug: event['content']['body']: ", event.get('content', {}).get('body', None))
	#
	# 	if event['type'] == "m.room.member":
	# 		if event['membership'] == "join":
	# 			print("{0} joined".format(event['content']['displayname']))
	# 	elif event['type'] == "m.room.message":
	# 		if event['content']['msgtype'] == "m.text":
	# 			print("{0}: {1}".format(event['sender'], event['content']['body']))
	# 	else:
	# 		print(event['type'])
		

	def talk(self, msg, type=MessageType.NOTICE):
		"""talk message in any type"""
		# log msg per line:
		logger.info("talk: message (type={} size={})".format(MessageType(type),len(msg)))
		for l in msg.splitlines():
			logger.info("talk: {}".format(repr(l)))

		# send message into chat room
		if MessageType(type) == MessageType.NOTICE:
			self.room.send_notice(msg)
		elif MessageType(type) == MessageType.TEXT:
			self.room.send_text(msg)
		elif MessageType(type) == MessageType.HTML:
			self.room.send_html(msg)

			
	def talk_text(self, msg):
		""" send_text """
		# log msg per line:
		logger.info("talk: message (size {})".format(len(msg)))
		for l in msg.splitlines():
			logger.info("talk: {}".format(repr(l)))

		# send message into chat room
		self.room.send_text(msg)
		
	def talk_html(self, msg):
		""" send_html """
		# log msg per line:
		logger.info("talk: message (size {})".format(len(msg)))
		for l in msg.splitlines():
			logger.info("talk: {}".format(repr(l)))

		# send message into chat room
		self.room.send_html(msg)
		

		

	def logout(self):
		self.client.logout()
		logger.info("bot logged out.")
		# print("DEBUG: bot --> logout")

