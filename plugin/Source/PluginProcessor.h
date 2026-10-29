#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "Playback.h"
#include "BuiltInSynth.h"

class ChordariumProcessor : public juce::AudioProcessor {
public:
    ChordariumProcessor();
    const juce::String getName() const override { return "Chordarium Studio"; }
    void prepareToPlay(double sr, int) override { sampleRate_ = sr; synth_.prepare(sr); }
    void releaseResources() override {}
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return true; }   // MIDI out for print-to-tracks (spike S1)
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*, int) override;

    // message-thread API used by the editor's native bridge
    void setSnapshotJson(const juce::String& json) { snapshot_ = json; }
    juce::String snapshot() const { return snapshot_; }
    void setNotes(std::vector<chordarium::Note> n, int64_t len);
    void previewPlay(double bpm) { freeBpm_ = bpm; freeQ_ = 0; playing_ = true; }
    void previewStop() { playing_ = false; }
    void setSyncHost(bool host) { syncHost_ = host; }
    void setLoop(bool on) { loop_ = on; }
    // Per-role mix (0 piano,1 bass,2 pad,3 drums). Mute/solo are applied by dropping events in processBlock.
    void setRoleMix(int role, bool mute, bool solo, float gain) { mute_[role] = mute; solo_[role] = solo; gain_[role] = gain; }
    bool takeNeedsRestore() { bool r = needsRestore_; needsRestore_ = false; return r; }
    double hostBpm() const { return lastBpm_.load(); }
private:
    double sampleRate_ = 44100, freeBpm_ = 90, freeQ_ = 0;
    std::atomic<bool> playing_ { false }, syncHost_ { false }, loop_ { true };
    std::atomic<bool> mute_[4] {}, solo_[4] {};
    std::atomic<float> gain_[4] { 0.8f, 0.8f, 0.8f, 0.8f };
    std::atomic<double> lastBpm_ { 90 };
    static int roleOfChannel(int ch) { return ch == 1 ? 0 : ch == 2 ? 1 : ch == 3 ? 2 : 3; }
    bool audible(int ch) const {
        bool anySolo = solo_[0] || solo_[1] || solo_[2] || solo_[3];
        int r = roleOfChannel(ch);
        return !mute_[r] && (!anySolo || solo_[r]);
    }
    chordarium::BuiltInSynth synth_;
    chordarium::Playback playback_;   // [TODO M4] replace with a lock-free double buffer; no allocation on the audio thread
    juce::String snapshot_;
    bool needsRestore_ = false;
    std::vector<chordarium::MidiOut> scratch_;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ChordariumProcessor)
};
