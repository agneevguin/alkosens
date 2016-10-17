"""Raspberry Pi Face Recognition Treasure Box
Positive Image Capture Script
Copyright 2013 Tony DiCola 

Run this script to capture positive images for training the face recognizer.

Failed images are stored in capture.pgm.

"""
import glob
import os
import sys
import select
import spidev
import cv2
import time
import config
import face
from random import randint
import RPi.GPIO as GPIO

ldr_channel = 0
PUSH_BUTTON = 26
#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)

def readadc(adcnum):
    # read SPI data from the MCP3008, 8 channels in total
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

# Sets up pins as inputs
def setup_in(*buttons):
	GPIO.setmode(GPIO.BCM)
	for button in buttons:
		GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Sets up pins as outputs
def setup_out(*leds):
	GPIO.setmode(GPIO.BCM)
	for led in leds:
		GPIO.setup(led, GPIO.OUT)
		GPIO.output(led, GPIO.LOW)

# Turn on and off the leds
def blink(*leds):
	# Blink all leds passed
	for led in leds:
		GPIO.output(led, GPIO.HIGH)
		time.sleep(0.5)
		GPIO.output(led, GPIO.LOW)

def led_on(*leds):
	for led in leds:
		GPIO.output(led, GPIO.HIGH)

def led_off(*leds):
	for led in leds:
		GPIO.output(led, GPIO.LOW)

# Prefix for positive training image filenames.
POSITIVE_FILE_PREFIX = 'positive_'
LED_RED = 17
LED_YEL = 27
LED_GRE = 22

def is_letter_input(letter):
	# Utility function to check if a specific character is available on stdin.
	# Comparison is case insensitive.
	if select.select([sys.stdin,],[],[],0.0)[0]:
		input_char = sys.stdin.read(1)
		return input_char.lower() == letter.lower()
	return False

if __name__ == '__main__':
	GPIO.cleanup()
	status = 'Start'
	setup_out(LED_RED, LED_YEL, LED_GRE)
	setup_in(PUSH_BUTTON)
	# Remove existing positive training images
	files = glob.glob('/home/pi/pi-facerec-box-master/training/positive/*')
	for f in files:
		os.remove(f)

	camera = config.get_camera()
	# Create the directory for positive training images if it doesn't exist.
	if not os.path.exists(config.POSITIVE_DIR):
		os.makedirs(config.POSITIVE_DIR)
	# Find the largest ID of existing positive images.
	# Start new images after this ID value.
	files = sorted(glob.glob(os.path.join(config.POSITIVE_DIR, 
		POSITIVE_FILE_PREFIX + '[0-9][0-9][0-9].pgm')))
	count = 0
	pic_count = 0
	check_count = 0
	training_complete = False
	button_pressed = False
	if len(files) > 0:
		# Grab the count from the last filename.
		count = int(files[-1][-7:-4])+1
	print 'Capturing positive training images.'
	print 'Press button or type c (and press enter) for blow test and image capture.'
	print 'Press Ctrl-C to quit.'
	try:
		while True:
			button = GPIO.input(PUSH_BUTTON)
			blink(LED_RED, LED_YEL, LED_GRE)
			if is_letter_input('c') or button == False:
				button_pressed = True
				break

		while True:
			if training_complete == False:
				button = GPIO.input(PUSH_BUTTON)
				# Check if button was pressed or 'c' was received, then capture image.
				if is_letter_input('c') or button == False or button_pressed == True:
					#while True:
						#button = GPIO.input(PUSH_BUTTON)
						#blink(LED_RED, LED_YEL, LED_GRE)
						#if is_letter_input('c') or button == False:
							#break
					# Remove existing positive training images
					files = glob.glob('/home/pi/pi-facerec-box-master/training/positive/*')
					for f in files:
						os.remove(f)

					led_off(LED_RED, LED_YEL, LED_GRE)
					time.sleep(1.5)
					led_on(LED_RED, LED_YEL, LED_GRE)
					button_pressed = False
					ldr_value = readadc(ldr_channel)
					print("LDR Value: %d" % ldr_value)
					if (ldr_value > 861):
						led_on(LED_RED)
						led_off(LED_YEL, LED_GRE)
					else:
						while True:
							print 'Capturing image...'
							image = camera.read()
							# Convert image to grayscale.
							image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
							# Get coordinates of single face in captured image.
							result = face.detect_single(image)
							if result is None:
								print 'Training. No face detected!!!' 
								pic_count +=1
								if pic_count > 10:
									break
								continue
							x, y, w, h = result
							# Crop image as close as possible to desired face aspect ratio.
							# Might be smaller if face is near edge of image.
							crop = face.crop(image, x, y, w, h)
							# Save image to file.
							filename = os.path.join(config.POSITIVE_DIR, POSITIVE_FILE_PREFIX + '%03d.pgm' % count)
							cv2.imwrite(filename, crop)
							print 'Found face and wrote training image', filename
							led_off(LED_RED, LED_YEL, LED_GRE)
							time.sleep(0.05)
							led_on(LED_RED, LED_YEL, LED_GRE)
							count += 1
							pic_count +=1
							time.sleep(0.2)
							if pic_count > 9: #2: ########################### 9
								break
						files = sorted(glob.glob(os.path.join(config.POSITIVE_DIR, POSITIVE_FILE_PREFIX + '[0-9][0-9][0-9].pgm')))
						if len(files) < 4: #1: ############################## 4
							print 'Not enough training images captured.'
							print 'Press button or type c (and press enter) to capture an image.'
							led_on(LED_YEL)
							led_off(LED_RED, LED_GRE)
							button_press = False
							pic_count = 0
							time.sleep(1)
							del image
							continue
						else:
							led_on(LED_GRE)
							led_off(LED_RED, LED_YEL)
							training_complete = True
							continue
			else:

				# Load captured training data into model
				print 'Loading training data...'
				model = cv2.createEigenFaceRecognizer()
				model.load(config.TRAINING_FILE)
				print 'Training data loaded!'

				faceDetected = False
				retest = True
				noFaceCount = 0
				while (faceDetected == False and retest == True):
					#'''COMMENT OUT TO REMOVE WAITING TIMES
					if check_count > 5: #1: ############################## 5
						randTestTime = randint(60,120) # randint(6,10) ############### randint(60,300)
						print 'Wait ', randTestTime, ' seconds for next test.'
						time.sleep(randTestTime)
						
					else:
						print 'Wait 15 seconds for next test.'
						time.sleep(15) ############################# 60

					#'''

					faceDetected = False
					while (faceDetected == False or time.time() - start_time > 45):
						# Check for the positive face and unlock if found.
						image = camera.read()
						print 'Testing image.'

						# Convert image to grayscale.
						image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
						# Get coordinates of single face in captured image.
						result = face.detect_single(image)
						start_time = time.time()
					
						if noFaceCount > 20:
							print 'Lost face. Could not find face!'
							led_on(LED_RED)
							led_off(LED_YEL, LED_GRE)
							check_count = 0
							faceDetected = True
							retest = False
						elif result is None:
							print 'Could not detect single face!!!', noFaceCount 
							faceDetected = False
							noFaceCount += 1
							led_on(LED_YEL)
							time.sleep(0.05)
							led_off(LED_YEL)
						else:
							x, y, w, h = result
							# Crop and resize image to face.
							crop = face.resize(face.crop(image, x, y, w, h))
							# Test face against model.
							label, confidence = model.predict(crop)
							print 'Predicted {0} face with confidence {1} (lower is more confident).'.format(
								'POSITIVE' if label == config.POSITIVE_LABEL else 'NEGATIVE', 
								confidence), label
							if confidence < config.POSITIVE_THRESHOLD: #and label == config.POSITIVE_LABEL:
								print 'Recognized face!'
								led_off(LED_RED, LED_YEL, LED_GRE)
								time.sleep(0.05)
								led_on(LED_GRE)
								check_count += 1
								faceDetected = True
							else:
								print 'Did not recognize face!'
								led_off(LED_RED, LED_YEL, LED_GRE)
								time.sleep(0.05)
								led_on(LED_RED)
								check_count = 0
								faceDetected = True
								retest = False
	# Stop on Ctrl+C and clean up
	except KeyboardInterrupt:
		GPIO.cleanup()
	except:
		print 'Exception captured. DEBUG DEBUG DEBUG!'
		led_on(LED_RED, LED_GRE)
		led_off(LED_YEL)

