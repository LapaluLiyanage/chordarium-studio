#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "CoreConnection.h"

ChordariumProcessor::ChordariumProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) { scratch_.reserve(512); }

void ChordariumProcessor::setNotes(std::vector<chordarium::Note> n, int64_t len) { playback_.setNotes(std::move(n), len); }

void ChordariumProcessor::processBlock(juce::AudioBuffer<float>& audio, juce::MidiBuffer& midi) {
    audio.clear();
    scratch_.clear();
    const double blockQ = audio.getNumSamples() / (sampleRate_ * 60.0 / freeBpm_);
    if (syncHost_) if (auto* ph = getPlayHead())
        if (auto pos = ph->getPosition(); pos && pos->getIsPlaying() && pos->getPpqPosition()) {
            // synced mode [TODO M4]: offset by the user's section start bar
            playback_.scheduleBlock(*pos->getPpqPosition(), blockQ, pos->getBpm().orFallback(freeBpm_), sampleRate_, false, scratch_), lastBpm_ = pos->getBpm().orFallback(freeBpm_);
        }
    if (playing_.load()) { playback_.scheduleBlock(freeQ_, blockQ, freeBpm_, sampleRate_, loop_, scratch_); freeQ_ += blockQ; }
    for (auto& e : scratch_) {
        if (!audible(e.channel)) continue;
        e.velocity = juce::jlimit(1, 127, int(e.velocity * gain_[roleOfChannel(e.channel)].load() / 0.8f));
        auto m = e.on ? juce::MidiMessage::noteOn(e.channel, e.pitch, (juce::uint8) e.velocity) : juce::MidiMessage::noteOff(e.channel, e.pitch);
        midi.addEvent(m, juce::jlimit(0, audio.getNumSamples() - 1, e.sampleOffset));
    }
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
    if (v.hasProperty("snapshot")) snapshot_ = v["snapshot"].toString();   // editor re-sends it to core on open
    if (v.hasProperty("syncHost")) syncHost_ = bool(v["syncHost"]);
    if (v.hasProperty("loop")) loop_ = bool(v["loop"]);
    if (auto* mix = v["mix"].getArray())
        for (int r = 0; r < juce::jmin(4, mix->size()); ++r)
            setRoleMix(r, bool((*mix)[r]["mute"]), bool((*mix)[r]["solo"]), float(double((*mix)[r]["gain"])));
    needsRestore_ = snapshot_.isNotEmpty();
}

juce::AudioProcessorEditor* ChordariumProcessor::createEditor() { return new ChordariumEditor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ChordariumProcessor(); }
