"""Raspberry Pi Face Recognition Treasure Box
Treasure Box Class
Copyright 2013 Tony DiCola 
"""
import time

import cv2
import RPIO
from RPIO import PWM

import picam
import config
import face


class Box(object):
	"""Class to represent the state and encapsulate access to the hardware of 
	the treasure box."""
	def __init__(self):
		# Initialize lock servo and button.
		self.servo = PWM.Servo()
		RPIO.setup(config.BUTTON_PIN, RPIO.IN)
		RPIO.setup(config.LED_RED, RPIO.OUT)
		RPIO.setup(config.LED_YELLOW, RPIO.OUT)
		RPIO.setup(config.LED_GREEN, RPIO.OUT)
		# Set initial box state.
		self.button_state = RPIO.input(config.BUTTON_PIN)
		self.is_locked = None

	def lock(self):
		"""Lock the box."""
		self.servo.set_servo(config.LOCK_SERVO_PIN, config.LOCK_SERVO_LOCKED)
		self.is_locked = True

	def unlock(self):
		"""Unlock the box."""
		self.servo.set_servo(config.LOCK_SERVO_PIN, config.LOCK_SERVO_UNLOCKED)
		self.is_locked = False

	def is_button_up(self):
		"""Return True when the box button has transitioned from down to up (i.e.
		the button was pressed)."""
		old_state = self.button_state
		self.button_state = RPIO.input(config.BUTTON_PIN)
		# Check if transition from down to up
		if old_state == config.BUTTON_DOWN and self.button_state == config.BUTTON_UP:
			# Wait 20 milliseconds and measure again to debounce switch.
			time.sleep(20.0/1000.0)
			self.button_state = RPIO.input(config.BUTTON_PIN)
			if self.button_state == config.BUTTON_UP:
				return True
		return False


	def blink(self):
		RPIO.output(config.LED_RED, True)
		time.sleep(0.5)
		RPIO.output(config.LED_RED, False)
		RPIO.output(config.LED_YELLOW, True)
		time.sleep(0.5)
		RPIO.output(config.LED_YELLOW, False)
		RPIO.output(config.LED_GREEN, True)
		time.sleep(0.5)
		RPIO.output(config.LED_GREEN, False)

	def on(self):
		RPIO.output(config.LED_RED, True)
		RPIO.output(config.LED_YELLOW, True)
		RPIO.output(config.LED_GREEN, True)

	def off(self):
		RPIO.output(config.LED_RED, False)
		RPIO.output(config.LED_YELLOW, False)
		RPIO.output(config.LED_GREEN, False)

	def red(self):
		RPIO.output(config.LED_RED, True)
		RPIO.output(config.LED_YELLOW, False)
		RPIO.output(config.LED_GREEN, False)

	def yellow(self):
		RPIO.output(config.LED_RED, False)
		RPIO.output(config.LED_YELLOW, True)
		RPIO.output(config.LED_GREEN, False)

	def green(self):
		RPIO.output(config.LED_RED, False)
		RPIO.output(config.LED_YELLOW, False)
		RPIO.output(config.LED_GREEN, True)

	def cleanup(self):
		RPIO.cleanup()
