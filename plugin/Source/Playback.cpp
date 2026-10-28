#include "Playback.h"
#include <cmath>

namespace chordarium {

void Playback::scheduleBlock(double startQ, double blockQ, double bpm, double sampleRate, bool loop, std::vector<MidiOut>& out) const {
    if (length_ <= 0) return;
    const double lenQ = ticksToQuarters(length_);
    const double samplesPerQ = sampleRate * 60.0 / bpm;
    auto emit = [&](double eventQ, const Note& n, bool on) {
        double rel = eventQ - startQ;
        if (rel < 0 || rel >= blockQ) return;
        out.push_back({int(rel * samplesPerQ), on, n.pitch, on ? n.velocity : 0, n.channel});
    };
    // Consider the block as positions in [startQ, startQ+blockQ); map to section time with wrap.
    const int firstCycle = loop ? int(std::floor(startQ / lenQ)) : 0;
    const int lastCycle = loop ? int(std::floor((startQ + blockQ) / lenQ)) : 0;
    for (int c = firstCycle; c <= lastCycle; ++c) {
        const double base = c * lenQ;
        for (const auto& n : notes_) {
            emit(base + ticksToQuarters(n.startTick), n, true);
            emit(base + ticksToQuarters(n.startTick + n.durationTick), n, false);
        }
    }
}

} // namespace chordarium
