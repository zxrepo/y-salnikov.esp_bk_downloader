#!/usr/bin/python2
# -*- encoding=UTF-8 -*-
import socket
import os, struct, array
from fcntl import ioctl

IP="192.168.0.31"
PORT=33333
GAMEPAD="/dev/input/js0"
ANALOG_THRESHOLD=0.3

BITMAP_AXIS={
	'hat0x':[0x01,0x02],
	'hat0y':[0x04,0x08],
	'x':[0x01,0x02],
	'y':[0x04,0x08]
}
BITMAP_BUTTONS={
	'a':0x10,
	'b':0x20,
	'x':0x40
}


# We'll store the states here.
axis_states = {}
button_states = {}

# These constants were borrowed from linux/input.h
axis_names = {
	0x00 : 'x',
	0x01 : 'y',
	0x02 : 'z',
	0x03 : 'rx',
	0x04 : 'ry',
	0x05 : 'rz',
	0x06 : 'trottle',
	0x07 : 'rudder',
	0x08 : 'wheel',
	0x09 : 'gas',
	0x0a : 'brake',
	0x10 : 'hat0x',
	0x11 : 'hat0y',
	0x12 : 'hat1x',
	0x13 : 'hat1y',
	0x14 : 'hat2x',
	0x15 : 'hat2y',
	0x16 : 'hat3x',
	0x17 : 'hat3y',
	0x18 : 'pressure',
	0x19 : 'distance',
	0x1a : 'tilt_x',
	0x1b : 'tilt_y',
	0x1c : 'tool_width',
	0x20 : 'volume',
	0x28 : 'misc',
}

button_names = {
	0x120 : 'trigger',
	0x121 : 'thumb',
	0x122 : 'thumb2',
	0x123 : 'top',
	0x124 : 'top2',
	0x125 : 'pinkie',
	0x126 : 'base',
	0x127 : 'base2',
	0x128 : 'base3',
	0x129 : 'base4',
	0x12a : 'base5',
	0x12b : 'base6',
	0x12f : 'dead',
	0x130 : 'a',
	0x131 : 'b',
	0x132 : 'c',
	0x133 : 'x',
	0x134 : 'y',
	0x135 : 'z',
	0x136 : 'tl',
	0x137 : 'tr',
	0x138 : 'tl2',
	0x139 : 'tr2',
	0x13a : 'select',
	0x13b : 'start',
	0x13c : 'mode',
	0x13d : 'thumbl',
	0x13e : 'thumbr',

	0x220 : 'dpad_up',
	0x221 : 'dpad_down',
	0x222 : 'dpad_left',
	0x223 : 'dpad_right',

	# XBox 360 controller uses these codes.
	0x2c0 : 'dpad_left',
	0x2c1 : 'dpad_right',
	0x2c2 : 'dpad_up',
	0x2c3 : 'dpad_down',
}

axis_map = []
button_map = []



def joy_init():
	# Iterate over the joystick devices.
	print('Available devices:')
	
	for fn in os.listdir('/dev/input'):
		if fn.startswith('js'):
			print('  /dev/input/%s' % (fn))
	# Open the joystick device.
	fn = GAMEPAD
	print('Opening %s...' % fn)
	jsdev = open(fn, 'rb')
	
	# Get the device name.
	#buf = bytearray(63)
	buf = array.array('c', ['\0'] * 64)
	ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
	js_name = buf.tostring()
	print('Device name: %s' % js_name)
	
	# Get number of axes and buttons.
	buf = array.array('B', [0])
	ioctl(jsdev, 0x80016a11, buf) # JSIOCGAXES
	num_axes = buf[0]
	
	buf = array.array('B', [0])
	ioctl(jsdev, 0x80016a12, buf) # JSIOCGBUTTONS
	num_buttons = buf[0]
	
	# Get the axis map.
	buf = array.array('B', [0] * 0x40)
	ioctl(jsdev, 0x80406a32, buf) # JSIOCGAXMAP
	
	for axis in buf[:num_axes]:
		axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
		axis_map.append(axis_name)
		axis_states[axis_name] = 0.0
	
	# Get the button map.
	buf = array.array('H', [0] * 200)
	ioctl(jsdev, 0x80406a34, buf) # JSIOCGBTNMAP
	
	for btn in buf[:num_buttons]:
		btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
		button_map.append(btn_name)
		button_states[btn_name] = 0
	
	print '%d axes found: %s' % (num_axes, ', '.join(axis_map))
	print '%d buttons found: %s' % (num_buttons, ', '.join(button_map))
	return jsdev

def main():
	sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	jsdev=joy_init()
	current_state=0x00;
	prev_state=0x00;
	sock.sendto("%c"%(0x00),(IP,PORT))
	# Main event loop
	while True:
		evbuf = jsdev.read(8)
		if evbuf:
			time, value, type, number = struct.unpack('IhBB', evbuf)
			if type & 0x80:
				print "(initial)",
			if type & 0x01:
				button = button_map[number]
				if button:
					button_states[button] = value
					if value:
						print "%s pressed" % (button)
						if button in BITMAP_BUTTONS.keys():
							current_state=current_state | BITMAP_BUTTONS[button]
					else:
						print "%s released" % (button)
						if button in BITMAP_BUTTONS.keys():
							current_state=current_state & (~BITMAP_BUTTONS[button])
			if type & 0x02:
				axis = axis_map[number]
				if axis:
					fvalue = value / 32767.0
					axis_states[axis] = fvalue
					print "%s: %.3f" % (axis, fvalue)
					if axis in BITMAP_AXIS.keys():
						if fvalue<(-ANALOG_THRESHOLD):
							current_state=current_state | BITMAP_AXIS[axis][0]
						else:
							if fvalue>ANALOG_THRESHOLD:
								current_state=current_state | BITMAP_AXIS[axis][1]
							else:
								current_state=current_state & (~(BITMAP_AXIS[axis][0] | BITMAP_AXIS[axis][1]))
			if current_state!=prev_state:
				sock.sendto("%c" % (current_state),(IP,PORT))
				prev_state=current_state
main()
