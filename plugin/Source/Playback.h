#pragma once
#include <cstdint>
#include <vector>

// Pure scheduling logic (no JUCE types) so it can be unit-tested anywhere. Audio-thread safe:
// the note vector is swapped in by the owner; scheduleBlock() never allocates beyond the caller's output vector capacity.
namespace chordarium {

constexpr int kPPQ = 480;

struct Note { int pitch; int64_t startTick; int64_t durationTick; int velocity; int channel; };
struct MidiOut { int sampleOffset; bool on; int pitch; int velocity; int channel; };

inline double ticksToQuarters(int64_t t) { return double(t) / kPPQ; }
inline int64_t quartersToTicks(double q) { return int64_t(q * kPPQ + 0.5); }

class Playback {
public:
    void setNotes(std::vector<Note> notes, int64_t lengthTicks) { notes_ = std::move(notes); length_ = lengthTicks; }
    // Emit note on/off events falling in [startQ, startQ + blockQ). Loops over the section length when loop is true.
    void scheduleBlock(double startQ, double blockQ, double bpm, double sampleRate, bool loop, std::vector<MidiOut>& out) const;
    int64_t lengthTicks() const { return length_; }
private:
    std::vector<Note> notes_;
    int64_t length_ = 0;
};

} // namespace chordarium
