import logging
import serial
import threading
import io

#
# Serial log reader + parser for NSC Solution F2 Brandmeld centrale
#


# Static parser data
MSG_END = '- - - - - - - - - - - - - - - - - - - - '

# enable logger
logger = logging.getLogger(__name__)



class Message(str):
	
	def __init__(self, raw):
		self.raw = raw
		
	def __str__(self):
		return self.raw
	
	def to_html(self):
		html = "<code>" + self.raw.replace("\n","<br>\n") + "</code>"
		return html


class LogReader:
	"""read and parse message from Brandmeld-installatie."""
	
	def __init__(self):
		# init buffer
		self._buf = []

		# serial reader loop boolean
		self.loop = False
		self.lock = threading.Lock() # Lock for self.lock | self._buf
		self._exit_graceful = False
		
		
		logger.info("LogReader ready.")
		
	
	def serial_open(self, serial_kwargs={}):
		"""Generator: read serial port and generate messages.
		
		# example:
		for message in self.serial_reader():
			...
		"""
		with self.lock:
			if self.loop:
				raise Exception("serial_reader already running.")
		
			# start loop
			self.loop = True
		
		# default timeout=1 
		serial_kwargs['timeout'] = serial_kwargs.get('timeout', 1)
		
		# baudrate -1 is None
		serial_kwargs['baudrate'] = serial_kwargs.get('baudrate', -1 )
		if serial_kwargs['baudrate'] == -1:
			del(serial_kwargs['baudrate'])


		# remove from serial kwargs (only for io wrapper)
		encoding = serial_kwargs.pop('encoding')
		
		# encoding = default 'cp437'?
		if encoding is None:
			encoding = 'cp437'
			
		#  serial open
		logger.info('Opening serial: {}'.format(str(serial_kwargs)))
		self.ser = serial.Serial(**serial_kwargs)
		logger.info('Connected serial port name: {}'.format(self.ser.name))
		# fix \r => \n using IOWrapper default behavior
		logger.info('Opening serial wrapper  encoding={}'.format(encoding))
		self.sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser), encoding=encoding)
		
	def serial_reader(self, serial_kwargs={}):
		# open serial
		self.serial_open(serial_kwargs)
		
		# no need to lock here, will catch race conditions at serial.SerialException
		while self.loop:
			line=None
			# read line or timeout
			try:
				# b'09-12-2021  13:59:00\rBevestiging \rIngang 01\r\r- - - - - - - - - - - - - - - - - - - - \r' 
				line = self.sio.readline().rstrip("\n")
				
			except serial.SerialException as e:
				logger.debug("SerialException ignored, self.loop is False: {} ".format(e))
				# ignore when self.loop is False 
				with self.lock:
					if self.loop:
						# oh no!
						logger.debug("SerialException ignored, self.loop is False: {} ".format(e))
						# resopen 
						self.serial_open(serial_kwargs)

						# raise e
				
			if line and line != "":
				logger.debug("serial readline: '{}'".format(repr(line)))
				
				# see if last line matches MSG_END 
				if line == MSG_END:
					# parse Message to callback
					message = (Message("\n".join(self._buf)))
					# flush buffer
					with self.lock:
						self._buf.clear()
					# return message
					yield(message)
					
					# end graceful 
					if self._exit_graceful:
						self.exit()
				else:
					with self.lock:
						self._buf.append(line)

		# end of loop
		logger.info('serial_reader loop ended.')



	def exit_graceful(self):
		"""gracefull exit, wait till end of incomming message."""
		self._exit_graceful = True

		# imediate stop when _buf is empty
		logger.info("exit_graceful()... (self.lock={})".format(self.lock.locked()))
		with self.lock:
			if len(self._buf) != 0:
				logger.info("exit_graceful()... (waiting for end of message..)")
				return
		# 
		self.exit()
			


		
	def exit(self):
		"""exit imidiate, incomming message will be lost"""
		# end loop
		with self.lock:
			if self.loop:
				self.loop = False
				logger.info("exit(): serial read loop")

		# close serial port.
		if self.ser and not self.ser.closed:
			self.ser.close()
			logger.info("exit(): serial closed.")	
		
		# notify none empty buffer:
		with self.lock:
			if len(self._buf) != 0:
				logger.info('serial_reader buffer not empty, this (partial)message is lost:')
				for line in self._buf:
					logger.info("serial_reader buffer::: '{}'".format(repr(line)))


