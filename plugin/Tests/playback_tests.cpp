#include "Playback.h"
#include <cassert>
#include <cstdio>
using namespace chordarium;

int main() {
    Playback p;
    p.setNotes({{60, 0, 480, 80, 1}, {64, 960, 480, 80, 1}}, 4 * kPPQ);
    std::vector<MidiOut> out;
    p.scheduleBlock(0.0, 1.0, 120.0, 48000.0, true, out);   // beat 0..1: note-on at 0, note-off at beat 1 excluded
    assert(out.size() == 1 && out[0].on && out[0].sampleOffset == 0);
    out.clear();
    p.scheduleBlock(1.5, 1.0, 120.0, 48000.0, true, out);   // beat 1.5..2.5: only second note-on at beat 2 (0.5 beat * 24000)
    assert(out.size() == 1 && out[0].pitch == 64 && out[0].sampleOffset == 12000);
    out.clear();
    p.scheduleBlock(3.5, 1.0, 120.0, 48000.0, true, out);   // wraps: cycle 1 note-on at beat 4 -> offset 0.5*24000
    assert(out.size() == 1 && out[0].pitch == 60 && out[0].sampleOffset == 12000);
    assert(quartersToTicks(1.0) == 480);
    std::puts("playback tests ok");
    return 0;
}
