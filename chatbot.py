
# element.io SDK
from matrix_client.client import MatrixClient, MatrixRequestError
from requests.exceptions import MissingSchema
import re
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

	
	def __init__(self, host, room, username=None, password=None, userid=None, token=None):
		if (username or password) and (userid or token):
			raise Exception(
				"You should either specify username and password " +
				"for login authentication, or userid and token for token " +
				"authentication, but not both.")
		if username and not password:
			raise Exception("Missing password")
		if userid and not token:
			raise Exception("Missing token")
		if not username and not userid:
			raise Exception("No authentication parameters specified")

		# keep false to preserve token.
		self.logout_on_exit = False 
		
		try:
			# connect with server
			self.client = MatrixClient(host, user_id=userid, token=token)
			logger.info("bot connected with host: {}".format(host))
			logger.info("matrix_client.client.ENCRYPTION_SUPPORT: {}".format(matrix_client.client.ENCRYPTION_SUPPORT))

			if username:
				self.client.login(username, password)
				self.logout_on_exit = True
				logger.info("bot connected as user: {}".format(username))

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
		
	def talk(self, body=None, body_html=None, notice=False):
		"""talk message in any type"""
		# log msg line:
		logger.info("talk: body={}, body_html={}, notice={})".format(repr(body), repr(body_html), notice))
		return self.send_message(body=body, body_html=body_html, notice=notice)

	def update_talk(self, event_id, new_body=None, body=None, body_html=None, new_body_html=None, room_id=None, notice=False):
		"""Update existing message. 
			a bit reversed engineerd but seems to work.
		"""
		logger.info("update: new_body={} new_body_html={} body={} body_html={})".format(repr(new_body), repr(body_html), repr(body), repr(body_html)))
		return self.send_message(event_id=event_id, body=body, new_body=new_body, body_html=body_html, new_body_html=new_body_html, room_id=room_id)

	def send_message(self, body=None, new_body=None, body_html=None, new_body_html=None, event_id=None, room_id=None, notice=False):
		# set our own room id if not defined.
		if not room_id:
			room_id = self.room.room_id
		
		content = {}

		if notice:
			content['msgtype'] = 'm.notice'
		else:
			content['msgtype'] = 'm.text'

		# add body of the update (for new messages, and for clients that do
		# not understand edits)
		if not body and body_html:
			body = re.sub('<[^<]+?>', '', body_html)
		elif not body:
			raise Exception("body or body_html is required")

		content['body'] = body
		if body_html:
			content['format'] = "org.matrix.custom.html"
			content['formatted_body'] = body_html

		if event_id:
			if not new_body and new_body_html:
				new_body = re.sub('<[^<]+?>', '', new_body_html)
			elif not new_body:
				raise Exception("new_body is required for updates")

			# This is the actual updated message as rendered by clients that
			# do understand edits
			content['m.new_content'] = {
				'msgtype': 'm.text',
				'body': new_body,
			}

			if new_body_html:
				content['m.new_content']['format'] = "org.matrix.custom.html"
				content['m.new_content']['formatted_body'] = new_body_html

			content['m.relates_to'] = {
				'rel_type': 'm.replace',
				'event_id': event_id,
			}
		else:
			if new_body or new_body_html:
				raise Exception("new_body and new_body_html only valid for updates")
		
		return self.client.api.send_message_event(room_id,'m.room.message', content)


	def logout(self):
		if self.logout_on_exit:
			self.client.logout()	
			logger.info("bot logged out.")
		else:
			logger.info("bot token is preserved.")
		


# vim: set noet ts=4 sw=4:
