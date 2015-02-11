# noodle
Old pygame based MIDI controllable sampler for nerdy musicians, with modest hardware requirements.

Sample banks are configurable with YAML files, and samples may be any file understood by pygame. Attempts to be smart about pre-loading samples to avoid latency, and handles several common scenarios for samples in live playback.
Originally developed for the band Radar Angel it was run under Debian on an Asus Eee PC 701 during live shows.

Tested with these MIDI controllers:

* Akai MPC2000XL via generic USB to MIDI adapter
* Akai LPD8 USB MIDI controller
* Korg microKORG via generic USB to MIDI adapter

Miscellaneous features:

* ANSII colour coded output while playing!
* Supports a large number of samples playing at once
* Supports multiple instances of the same sample at once
* Allows arbitrarily mapping MIDI notes to samples
* Supports pre-definition of multiple MIDI inputs in a single "song"
* Map any channel to "increment", "decrement" and "reset" actions on a counter, and display this onscreen (for counting cues etc)
* Convenient YAML format for "song" files allows for quick tweaking of songs during rehearsal
* Plenty of per-sample flags to save having to make every sample perfect on disk
* Supports MIDI devices which send a "note velocity changed to zero" message instead of the usual `note_off` message

Supports these flags on samples:

* `debounce` for old keyboards which don't always send a single `note_on` message per key press
* `no_overlap` for samples which should stop any existing instances of the sample playing before playing again
* `pan` to set left / right channel pan
* `fade_out` to add a fade-out effect when the sample stops playing
* `one_shot` to specify that a sample should continue playing when the key is released

A number of Radar Angel song files including the button mappings for the Akai MPC are provided in the `examples` directory.
