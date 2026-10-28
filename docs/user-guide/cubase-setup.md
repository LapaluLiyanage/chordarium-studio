# Cubase 15 setup (optional Cubase link + template)

1. Install loopMIDI and create a port named exactly `Chordarium Remote`.
2. Copy `Chordarium_Studio.js` to `Documents\Steinberg\Cubase\MIDI Remote\Driver Scripts\Local\Chordarium\Studio\` (the installer can do this).
3. In Cubase: Studio > MIDI Remote Manager, check that "Chordarium Studio" is listed and mapped to the port.
4. Add an instrument track with Chordarium Studio, then four MIDI tracks (Piano ch 1, Bass ch 2, Pad ch 3, Drums ch 10)
   with Input = "Chordarium Studio MIDI Out" filtered to that channel, output to your instruments. Save as a template.
5. Press Play in the plugin: transport buttons in the plugin send CC 20–24 on channel 16.
