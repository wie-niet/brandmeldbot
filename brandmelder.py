import logging
import serial
import threading
import io
import time

from enum import Enum

#
# Serial log reader + parser for NSC Solution F2 Brandmeld centrale
#

# enable logger
logger = logging.getLogger(__name__)




class Parser:
	# Config:
	END_OF_MESSAGE = '- - - - - - - - - - - - - - - - - - - - '
	STRPTIME_FORMAT = '%d-%m-%Y %H:%M:%S'
	INFERTILITY_SECS = 2 # how mucht seconds is maximum between BMC timstamp of parent vs. child messages.

	# Cache:
	COLLECTED_ALARMS = []
	CURRENT_PARENT_MSG = None

	@staticmethod
	def setParent(parent):
		# setting new parent, flush previous
		Parser.flush()
		
		# set new parent:
		Parser.CURRENT_PARENT_MSG = parent
	
	
	@staticmethod
	def addChild(child):
		parent = Parser.CURRENT_PARENT_MSG

		# If no parent, it does not accept children or is too old, then the current message becomes a parent instead
		if not parent:
			logger.debug("No parent, upgrading secondary")
			Parser.setParent(child)
		elif not parent.fertility:
			logger.debug("Parent not fertile, upgrading secondary")
			Parser.setParent(child)
		elif parent.bmc_time + Parser.INFERTILITY_SECS >= child.bmc_time:
			logger.debug("Parent too old, upgrading secondary")
			Parser.setParent(child)
		else:
			# add child to parent
			parent.childs.append(child)	
			# add parent to child
			child.parent = parent
			
		
	@staticmethod
	def clock():
		pass
		# check if parent needs to flush


	@staticmethod
	def flush():
		pass
		## flush current parent


class Message:
	
	class HierarchyType(Enum):
		PRIMARY=1   # reason/cause
		SECONDARY=2 # effects/consequence
		UNKNOWN=0

	class Priority(Enum):
		HIGH=3   
		NORMAL=2 
		LOW=1    
		UNKNOWN=0
	
	class Fertility(Enum):
		CAN_HAVE_CHILDREN=True	
		CAN_NOT_HAVE_CHILDREN=False
		NOT_SET=None
	
	def __init__(self, raw, meta):
		# add raw body content (str)
		self.lines = [l.strip() for l in raw.splitlines()]
		
		# add meta data (dict)
		self.meta = meta
		# meta['secs_before']   
		# meta['time_begin']    
		# meta['secs_duration'] 

		## line 1: date + time   -> self.bmc_time (str)
		## line 2: status        -> self.status   (str)
		## line 2: subject       -> self.subject  ([str, str, ...])

		# # hierarchy type
		# self.hierarchy = self.HierarchyType.UNKNOWN
		# self.prio = self.Priority.UNKNOWN
		# self.fertility = self.Fertility.NOT_SET
		#
		# # placeholder for my parent
		# self.parent = None
		#
		# # placeholder for our childrens
		# self.childs = []
		
		# do magic
		self._parser()
		
		
		# 
		# proces layout
		# self.body = '|'.join(raw.splitlines()[1:])
		self.body = f'{self.status}: {self.subject} \n[{self.prio}, {self.hierarchy}]'

		# logger.info("message: meta[{:.2f},{:.2f},{:.2f}] '{}' #{}:'{}' ".format(
		# 	self.meta.get('secs_before', 0),
		# 	self.meta.get('time_begin', 0), # time.strftime( '%d-%m-%Y %H:%M:%S', time.gmtime(  ....  ))
		# 	self.meta.get('secs_duration', 0),
		# 	self.hierarchy,
		# 	len(self.raw.splitlines()),
		# 	self.body
		# ))
		logger.info("messagage## msg = {}".format(repr(self)))
		logger.info("messagage _parsed: {}, {}, {}".format(self.hierarchy, self.prio, self.fertility))
	
	def _parser(self):
		# rule 1: status == "Alarm" -> High priority primary with secondaries, + collect subject in active_alarm_cache
		if self.status == "Alarm":
			logger.debug("_parser match Rule 1")
			self.prio = self.Priority.HIGH
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(True)
			
			# add line 2 (subect) to the COLLECTED_ALARMS
			if self.subject not in Parser.COLLECTED_ALARMS:
				Parser.COLLECTED_ALARMS.append(self.subject)
					
		# rule 2: status == "Hoofdalarm" -> High priority secondary with secondaries (this one is just to make sure that "Hoofdalarm" becomes high prio, even when not preceded by a regular alarm)
		elif self.status == "Hoofdalarm":
			logger.debug("_parser match Rule 2")
			self.prio = self.Priority.HIGH
			self.hierarchy = self.HierarchyType.SECONDARY
			self.fertility = self.Fertility(True)
			
		# rule 3: status == "Storing" -> High priority primary with secondaries
		elif self.status == "Storing":
			logger.debug("_parser match Rule 3")
			self.prio = self.Priority.HIGH
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(True)
			
		# rule 4: status == "Geactiveerd" -> Normal priority secondary without secondaries (without secondaries because I think this is never the cause of something, but I'm not entirely sure)
		elif self.status == "Geactiveerd":
			logger.debug("_parser match Rule 4")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.SECONDARY
			self.fertility = self.Fertility(False)

		# rule 5: status == "In rust" -> Normal priority secondary with secondaries (this will often be triggered as a secondary, but might also be upgraded to a primary when triggered first)
		elif self.status == "In rust":
			logger.debug("_parser match Rule 5")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.SECONDARY
			self.fertility = self.Fertility(True)
				
		# rule 6: status == "BMC Reset" -> Normal priority primary with secondaries
		elif self.status == "BMC Reset":
			logger.debug("_parser match Rule 6")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(True)
			
		# rule 7: status == "Aan" || status == "Uit" -> Normal priority secondary with secondaries ( ???-> Also expected to occur as primary or secondary, for example when disabling all sounders or all doormeldingen, etc.)
		elif self.status == "Aan" or self.status == "Uit":
			logger.debug("_parser match Rule 7")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.SECONDARY
			self.fertility = self.Fertility(True)
			
		# rule 8.1.a: status == "Informatie" && subject matches "Ring .. protocol error 0000" -> Low priority primary without secondaries
		elif self.status == "Informatie" and " protocol error 0000" in self.subject:
			logger.debug("_parser match Rule 8.1.a")
			self.prio = self.Priority.LOW
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(False)

		# rule 8.1.b: status == "Informatie" && subject matches "Ring .. protocol error ...." -> Normal priority primary without secondaries
		elif self.status == "Informatie" and " protocol error " in self.subject:
			logger.debug("_parser match Rule 8.1.b")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(False)
			
		# rule 8.2: status == "Informatie" && subject matches "Tijdprogramma.*" -> Low priority primary with secondaries
		elif self.status == "Informatie" and "Tijdprogramma " in self.subject:
			logger.debug("_parser match Rule 8.2")
			self.prio = self.Priority.LOW
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(True)
			
		# rule 8.z: status == "Informatie" -> Normal priority primary without secondaries
		elif self.status == "Informatie":
			logger.debug("_parser match Rule 8.z")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(False)
		
		# rule (All others) -> Normal priority primary without secondaries
		else:
			logger.debug("_parser match Rule 'All others'")
			self.prio = self.Priority.NORMAL
			self.hierarchy = self.HierarchyType.PRIMARY
			self.fertility = self.Fertility(False)
			

		#
		# let's setup our ancestor tree
		#
		self.parent = None			# placeholder for primary
		self.childs = []      		# placeholder for secondaries
		
		if self.hierarchy == self.HierarchyType.PRIMARY:			
			# primary messages always become the new parent
			logger.debug("_parser: setParent'")
			Parser.setParent(self)
		else:
			# make my parent aware of me, their newborn child
			logger.debug("_parser: addChild'")
			Parser.addChild(self)

		
	@property	
	def bmc_time_str(self):
		"""parse time from Brand Meld Centrale (line[0] in log)"""
		return(self.lines[0])

	@property	
	def bmc_time(self):
		"""parse time from Brand Meld Centrale (line[0] in log)"""
		try:
			return time.mktime(time.strptime(self.bmc_time_str, Parser.STRPTIME_FORMAT))
		except ValueError as e:	
			logger.warning('bmc_time mktime error: {}. (msg= {})'.format(e, repr(self)))
			raise(e)

		
	@property
	def status(self):
		"""parse status from Brand Meld Centrale (line[1] in log)"""
		return self.lines[1]
		
	@property
	def subject(self):
		"""parse subject from Brand Meld Centrale (line[2:] in log)"""
		return '\n'.join(self.lines[2:])	

	def __str__(self):
		# return self.raw
		return self.body

	def __repr__(self):
		# return self.raw
		return f'{self.__class__.__name__}({repr(self.lines)}, {repr(self.meta)})'
	
	def to_html(self):
		# html = "<code>" + self.__str__().replace("\n","<br>\n") + "</code>"
		html = f'<b>{self.status}</b> {self.subject} <br>\n'
		
		# add child html:
		if len(self.childs) != 0:
			html += "<details><ul>\n"
			
			for c in self.childs:
				html += '<li>' + c.to_html() + '</li>'

			html += "<ul></details>\n"


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
		"""Open serial port"""
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
		"""Generator: read serial port and generate messages.
		
		# example:
		for message in obj.serial_reader():
			...
		"""
		# open serial
		self.serial_open(serial_kwargs)
		
		# datetime tracking for meta_data
		secs_before   = None
		time_begin    = None
		time_end      = time.time()
		secs_duration = None  # i am just curious for abnormalities
		
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
				
				# see if last line matches Parser.END_OF_MESSAGE 
				if line == Parser.END_OF_MESSAGE:
					# meta data: time_end of this message
					time_end  = time.time()
					secs_duration = time_end - time_begin

					# parse Message to callback
					message = Message("\n".join(self._buf), {
							'secs_before': round(secs_before, 2),    # keep precision readable
							'time_begin':round(time_begin, 2),       # keep precision readable
							'secs_duration':round(secs_duration, 2)  # keep precision readable
						})
					# flush buffer
					with self.lock:
						self._buf.clear()
						
					# return message
					yield(message)
					
					# end graceful 
					if self._exit_graceful:
						self.exit()
				else:
					# meta data: time_begin of this message
					if len(self._buf) == 0:
						time_begin  = time.time()
						secs_before = time_begin - time_end # new begin - prev. end
					
					with self.lock:
						self._buf.append(line)
			# else:
			# 	# timeout serial.readline()

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



# vim: set noet ts=4 sw=4:
