#include "PluginProcessor.h"
#include <algorithm>
#include "PluginEditor.h"
#include "CoreConnection.h"

ChordariumProcessor::ChordariumProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) { scratch_.reserve(512); }

void ChordariumProcessor::setNotes(std::vector<chordarium::Note> n, int64_t len) {
    const juce::SpinLock::ScopedLockType lock(notesLock_);
    playback_.setNotes(std::move(n), len);
}

void ChordariumProcessor::processBlock(juce::AudioBuffer<float>& audio, juce::MidiBuffer& midi) {
    audio.clear();
    scratch_.clear();
    if (panic_.exchange(false)) { synth_.allOff(); midi.addEvent(juce::MidiMessage::allNotesOff(1), 0); midi.addEvent(juce::MidiMessage::allNotesOff(2), 0); midi.addEvent(juce::MidiMessage::allNotesOff(3), 0); midi.addEvent(juce::MidiMessage::allNotesOff(10), 0); }
    const juce::SpinLock::ScopedTryLockType tryLock(notesLock_);   // if the UI is swapping notes right now, skip scheduling this block
    const double blockQ = audio.getNumSamples() / (sampleRate_ * 60.0 / freeBpm_);
    bool uiPlaying = false;
    if (tryLock.isLocked()) {
    if (syncHost_) if (auto* ph = getPlayHead())
        if (auto pos = ph->getPosition(); pos && pos->getIsPlaying() && pos->getPpqPosition()) {
            // synced mode [TODO M4]: offset by the user's section start bar
            uiPlaying = true, shownQ_ = *pos->getPpqPosition(), playback_.scheduleBlock(*pos->getPpqPosition(), blockQ, pos->getBpm().orFallback(freeBpm_), sampleRate_, false, scratch_), lastBpm_ = pos->getBpm().orFallback(freeBpm_);
        }
    if (playing_.load()) { playback_.scheduleBlock(freeQ_, blockQ, freeBpm_, sampleRate_, loop_, scratch_); freeQ_ += blockQ; uiPlaying = true; shownQ_ = freeQ_; }
    shownPlaying_ = uiPlaying;
    }
    std::sort(scratch_.begin(), scratch_.end(), [](const chordarium::MidiOut& a, const chordarium::MidiOut& b) { return a.sampleOffset < b.sampleOffset; });
    const int n = audio.getNumSamples();
    float* left = audio.getWritePointer(0);
    float* right = audio.getNumChannels() > 1 ? audio.getWritePointer(1) : left;
    const bool soundOn = builtIn_.load();
    if (!soundOn) synth_.allOff();   // let nothing ring on after muting
    int cursor = 0;
    for (auto& e : scratch_) {
        if (!audible(e.channel)) continue;
        e.velocity = juce::jlimit(1, 127, int(e.velocity * gain_[roleOfChannel(e.channel)].load() / 0.8f));
        const int at = juce::jlimit(0, n - 1, e.sampleOffset);
        if (at > cursor) { if (soundOn) synth_.render(left + cursor, right + cursor, at - cursor); cursor = at; }   // built-in preview sound
        if (soundOn) { if (e.on) synth_.noteOn(e.channel, e.pitch, e.velocity); else synth_.noteOff(e.channel, e.pitch); }
        auto m = e.on ? juce::MidiMessage::noteOn(e.channel, e.pitch, (juce::uint8) e.velocity) : juce::MidiMessage::noteOff(e.channel, e.pitch);
        midi.addEvent(m, at);
    }
    if (cursor < n && soundOn) synth_.render(left + cursor, right + cursor, n - cursor);
}

void ChordariumProcessor::getStateInformation(juce::MemoryBlock& dest) {
    // Refresh the cached snapshot from core when it is up; otherwise keep the last one we had (spec 9.3).
    auto info = CoreConnection::discover();
    auto fresh = CoreConnection::getSnapshot(info);
    if (fresh.isNotEmpty()) snapshot_ = fresh;
    auto* o = new juce::DynamicObject();
    o->setProperty("version", 1);
    o->setProperty("snapshot", snapshot_);
    o->setProperty("syncHost", syncHost_.load());
    o->setProperty("loop", loop_.load());
    o->setProperty("builtInSound", builtIn_.load());
    juce::Array<juce::var> mix;
    for (int r = 0; r < 4; ++r) {
        auto* m = new juce::DynamicObject();
        m->setProperty("mute", mute_[r].load()); m->setProperty("solo", solo_[r].load()); m->setProperty("gain", double(gain_[r].load()));
        mix.add(juce::var(m));
    }
    o->setProperty("mix", mix);
    auto text = juce::JSON::toString(juce::var(o), true);
    dest.append(text.toRawUTF8(), text.getNumBytesAsUTF8());
}

void ChordariumProcessor::setStateInformation(const void* data, int size) {
    auto v = juce::JSON::parse(juce::String::fromUTF8((const char*) data, size));
    if (!v.isObject()) return;
    sessionInitialised_ = true;   // this instance belongs to a saved project: keep its song, do not reset core
    if (v.hasProperty("snapshot")) snapshot_ = v["snapshot"].toString();   // editor re-sends it to core on open
    if (v.hasProperty("syncHost")) syncHost_ = bool(v["syncHost"]);
    if (v.hasProperty("loop")) loop_ = bool(v["loop"]);
    if (v.hasProperty("builtInSound")) builtIn_ = bool(v["builtInSound"]);
    if (auto* mix = v["mix"].getArray())
        for (int r = 0; r < juce::jmin(4, mix->size()); ++r)
            setRoleMix(r, bool((*mix)[r]["mute"]), bool((*mix)[r]["solo"]), float(double((*mix)[r]["gain"])));
    needsRestore_ = snapshot_.isNotEmpty();
}

juce::AudioProcessorEditor* ChordariumProcessor::createEditor() { return new ChordariumEditor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ChordariumProcessor(); }
