#!/usr/bin/python -u

"""
Pygame based MIDI controllable synthesizer for nerdy musicians, with modest hardware requirements.

Copyright (C) 2012 Michael Fincham <michael@hotplate.co.nz>.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import pypm
import pygame
import yaml
import sys
import time

MIDI_CHANNELS = 16
MIDI_MESSAGE_STATUSES = { 128: 'note_off', 144: 'note_on', 176: 'control_change' }

AUDIO_SAMPLE_RATE = 44100
AUDIO_BITS = -16 # unsigned 16 bit
AUDIO_CHANNELS = 2   # 1 == mono, 2 == stereo
AUDIO_BUFFER_SIZE = 512 # audio buffer size in no. of samples

LOGGING = { 'midi': False, 'player': True, 'main': True }

samples = {}
instruments = []

counter = 0

class NoodleError(Exception):
    pass
    
class NoodleInstrumentNotFoundError(NoodleError):
    pass
    
class NoodleImpossibleInstrumentDefinitionError(NoodleError):
    pass

class NoodleImpossibleSampleDefinitionError(NoodleError):
    pass

class NoodleMidiStatusUnrecognisedError(NoodleError):
    pass

class Colors():
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

class Sample():

    def __init__(self, path, one_shot=True, fade_out=None, instrument=None, pan=127, no_overlap=False, debounce=0):
        if path is None:
            raise NoodleImpossibleSampleDefinitionError("You must specify a path to the sample.")
        self.player = pygame.mixer.Sound(path)
        self.path = path
        self.one_shot = one_shot
        self.fade_out = fade_out
        self.instrument = instrument
        self.pan = pan
        self.no_overlap = no_overlap
        self.counter = 0
        self.debounce = debounce / 1000.0 if debounce > 0 else None
        self.last_played = time.time()

    def __str__(self):
        return self.path

    def play(self):
        if self.debounce is not None:
            now = time.time()
            if now > self.last_played + self.debounce:
                self.last_played = now
            else:
                log('player','Ignored keybounce for %s' % self.path)
                return
            
        global counter
        if self.path == 'COUNT_UP':
	        counter = counter + 1
	        log('player',"*** Counter is %i" % counter)
	        return
        if self.path == 'COUNT_RESET':
	        counter = 0
	        log('player',"Counter reset")
	        return
        if self.no_overlap:
            self.stop()
        channel = self.player.play()
        if self.pan != 127:
            left_volume = 1.0 - float(self.pan) / 255
            right_volume = float(self.pan) / 255
            channel.set_volume(left_volume,right_volume)
            
        log('player', (Colors.GREEN if not self.one_shot else Colors.BLUE) + "P" + Colors.END + " %s" % str(self))
        
    def stop(self):
        if self.fade_out is None:
            self.player.stop()
        else:
            self.player.fadeout(self.fade_out)
        log('player', Colors.YELLOW + ('S' if self.fade_out is None else 'F') + Colors.END + " %s" % str(self))

class Instrument():

    def __init__(self, name=None, device_number=None, zero_velocity_for_note_off=False, uid=None):
        if name is None and device_number is None:
            raise NoodleImpossibleInstrumentDefinitionError
        self.name = name
        self.uid = uid if uid is not None else repr(self)
        self.device_number = device_number
        self.zero_velocity_for_note_off = zero_velocity_for_note_off

        for device_number in range(pypm.CountDevices()):
            interface, name, input_device, output_device, opened = pypm.GetDeviceInfo(device_number)
            if input_device == 1:
                if self.name in name or self.device_number == device_number:
                    self.midi_device = pypm.Input(device_number)
                    self.midi_device.SetFilter(pypm.FILT_REALTIME)
                    log('main',Colors.BLUE + (" %s attached!" % self.uid) + Colors.END)                    
                    return
        raise NoodleInstrumentNotFoundError(repr(self))

    def __str__(self):
        return self.name if self.name is not None else self.uid

    def midi_status_decode(self, status_code, data_two):
        for candidate_status_code in MIDI_MESSAGE_STATUSES:
            if status_code >= candidate_status_code and status_code <= candidate_status_code + MIDI_CHANNELS - 1:
                status = MIDI_MESSAGE_STATUSES[candidate_status_code]
                if self.zero_velocity_for_note_off and status == 'note_on' and data_two == 0: # weird dumb MIDI devices like the MPC2000XL do this
                    status = 'note_off'
                return (status, status_code - candidate_status_code) # return a tuple of the status and the channel
        raise NoodleMidiStatusUnrecognisedError

def log(facility, message):
    assert facility in LOGGING
    if LOGGING[facility]:
        print "%s: %s" % (facility, message)    
  
def main():

    log('main',"Noodle starting up!")
    
    config_file = file(sys.argv[1],'r')
    config = yaml.load(config_file)
    
    log('main',"Attaching instruments...")
    pypm.Initialize()
    
    for device_number in range(pypm.CountDevices()):
        interface, name, input_device, output_device, opened = pypm.GetDeviceInfo(device_number)
        log('main'," Device %i, %s %s" % (device_number, name, '(input)' if input_device == 1 else '(not input, ignored)'))
        
    for instrument in config['instruments']:
        try:
            instruments.append(Instrument(uid=instrument.get('uid', None), name=instrument.get('name', None), device_number=instrument.get('device_number', None), zero_velocity_for_note_off=instrument.get('zero_velocity_for_note_off', False)))
        except NoodleInstrumentNotFoundError as e:
            log('main',Colors.YELLOW + " No device found matching: " + Colors.END + " %s" % repr(instrument))
    
    if len(instruments) == 0:
        log('main',Colors.RED + "No instruments found. Quitting." + Colors.END)
        sys.exit(1)
   
    log('main',"Loading samples...")

    pygame.mixer.init(AUDIO_SAMPLE_RATE, AUDIO_BITS, AUDIO_CHANNELS, AUDIO_BUFFER_SIZE)
    pygame.mixer.set_num_channels(128)

    for sample_definition in config['samples']:
        if sample_definition['note'] not in samples:
            samples[sample_definition['note']] = []
        samples[sample_definition['note']].append(Sample(sample_definition.get('path',None), one_shot=sample_definition.get('one_shot',False), fade_out=sample_definition.get('fade_out',None), instrument=sample_definition.get('instrument',None), pan=sample_definition.get('pan',127), no_overlap=sample_definition.get('no_overlap', False), debounce=sample_definition.get('debounce', 0)))

    log('main',Colors.PURPLE + "Ready!" + Colors.END)
       
    while True:
        for instrument in instruments:
            while instrument.midi_device.Poll():
                message = instrument.midi_device.Read(1)
                status_code, data_one, data_two, sysex = message[0][0]
                
                try:
                    status, channel = instrument.midi_status_decode(status_code, data_two)
                except NoodleMidiStatusUnrecognisedError:
                    log('midi',"Unrecognised MIDI status code.")

                log('midi',"%s, channel %i, data_one %i, data_two %i" % (status, channel, data_one, data_two))
                
                              
                try:
                    if status != 'control_change':
                        this_note_samples = samples[data_one] 
                        for sample in this_note_samples:
                            if sample.instrument is None or instrument.uid == sample.instrument:
                                if status == 'note_on':
                                    sample.play()
                                elif status == 'note_off':
                                    if not sample.one_shot:
                                        sample.stop()
                except KeyError as e:
                    log('player',Colors.RED + "E" + Colors.END + " No sample for note %i on channel %i" % (e[0], channel))
                        
if __name__ == '__main__':
    main()

