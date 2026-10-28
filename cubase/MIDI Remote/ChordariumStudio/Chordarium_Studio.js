// Chordarium Studio — optional Cubase MIDI Remote script (spec section 12.1).
// Install to: Documents\Steinberg\Cubase\MIDI Remote\Driver Scripts\Local\Chordarium\Studio\
// Listens on the loopMIDI port "Chordarium Remote", MIDI channel 16, CC 20..24 (value 127 = trigger):
//   20 play, 21 stop, 22 record, 23 return to start, 24 add marker.
// [VERIFY] Written from the documented midiremote_api_v1 shape; check every call against the API
// reference that ships in Cubase's MIDI Remote folder before relying on it (docs/decisions/S4-midi-remote.md).
var midiremote_api = require('midiremote_api_v1')

var driver = midiremote_api.makeDeviceDriver('Chordarium', 'Studio', 'Chordarium')
var PORT = 'Chordarium Remote'

var midiInput = driver.mPorts.makeMidiInput()
driver.makeDetectionUnit().detectPortPair(midiInput, driver.mPorts.makeMidiOutput())
    .expectInputNameEquals(PORT)
    .expectOutputNameEquals(PORT)

var surface = driver.mSurface
var CHANNEL = 15 // channel 16, zero-based
var buttons = [
    { name: 'Play', cc: 20, x: 0 },
    { name: 'Stop', cc: 21, x: 2 },
    { name: 'Record', cc: 22, x: 4 },
    { name: 'To Start', cc: 23, x: 6 },
    { name: 'Marker', cc: 24, x: 8 }
]
var objs = buttons.map(function (b) {
    var btn = surface.makeButton(b.x, 0, 2, 2)
    btn.setShapeCircle()
    btn.mSurfaceValue.mMidiBinding.setInputPort(midiInput).bindToControlChange(CHANNEL, b.cc)
    return btn
})

var page = driver.mMapping.makePage('Chordarium')
var t = page.mHostAccess.mTransport.mValue
page.makeValueBinding(objs[0].mSurfaceValue, t.mStart)
page.makeValueBinding(objs[1].mSurfaceValue, t.mStop)
page.makeValueBinding(objs[2].mSurfaceValue, t.mRecord)
page.makeValueBinding(objs[3].mSurfaceValue, t.mRewind) // [VERIFY] a true "return to zero" binding may be a command instead
page.makeCommandBinding(objs[4].mSurfaceValue, 'Transport', 'Insert Marker')
