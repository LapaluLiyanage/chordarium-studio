# Getting the arrangement into Cubase

Chordarium Studio cannot create Cubase tracks itself (Cubase does not allow a plugin to do that), so the parts reach Cubase as MIDI. There are three ways, from quickest to most flexible.

## 1. Drag the whole section (one track per part)

1. Arrange the section (Piano, Bass, Pad and Drums lanes appear).
2. Press and drag **⠿ Drag all to Cubase** (next to Re-arrange) out of the plugin window and drop it on an **empty area of the Cubase project window**.
3. Cubase creates one MIDI track for each part, named Piano, Bass, Pad and Drums.
4. On each new MIDI track, set the **Output** to the instrument you want (for example a Kontakt track or any VST instrument track). Or drag the MIDI part onto an existing instrument track instead.

## 2. Drag a single part

Press and drag the **name area of a lane** (the coloured box with "Piano", "Bass"…) and drop it on an **instrument track** or MIDI track. The part lands at the position where you drop it.

If a drag does nothing, check that the left mouse button is held while you move, and drag at least a few pixels before leaving the plugin window.

## 3. Export a file and import it

1. Press **Export section** (or **Export song**) at the bottom of the plugin. Windows Explorer opens on the file.
2. In Cubase use **File > Import > MIDI File…**, or drag the file from Explorer onto the project window.

The files are kept in `%APPDATA%\ChordariumStudio\exports\`.

## Recording the plugin's MIDI output instead

The plugin also plays its parts out of its MIDI output on channels 1 (piano), 2 (bass), 3 (pad) and 10 (drums). Create a MIDI track, set its **Input** to the Chordarium Studio MIDI output, arm it and record while the section plays. This is the way to capture exactly what you hear, and it needs one pass per part (or one pass with all channels).

## Hearing it

The plugin has a small built-in preview sound so that **Play** is audible. For real instruments, route the MIDI to your own VST instrument tracks as above.
