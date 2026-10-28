#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "Playback.h"

class ChordariumProcessor : public juce::AudioProcessor {
public:
    ChordariumProcessor();
    const juce::String getName() const override { return "Chordarium Studio"; }
    void prepareToPlay(double sr, int) override { sampleRate_ = sr; }
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
private:
    double sampleRate_ = 44100, freeBpm_ = 90, freeQ_ = 0;
    std::atomic<bool> playing_ { false };
    chordarium::Playback playback_;   // [TODO M4] replace with a lock-free double buffer; no allocation on the audio thread
    juce::String snapshot_;
    std::vector<chordarium::MidiOut> scratch_;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ChordariumProcessor)
};
