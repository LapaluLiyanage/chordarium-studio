#pragma once
#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

// WebView host. [VERIFY] exact JUCE 8 WebBrowserComponent::Options API (withNativeIntegrationEnabled,
// withResourceProvider, withNativeFunction, emitEventIfBrowserIsVisible) against the JUCE 8 docs before M4 sign-off.
class ChordariumEditor : public juce::AudioProcessorEditor, public juce::DragAndDropContainer, private juce::Timer {
public:
    explicit ChordariumEditor(ChordariumProcessor&);
    ~ChordariumEditor() override;
    void resized() override { web_->setBounds(getLocalBounds()); }
    void timerCallback() override;   // pushes transport position to the UI so Live chord and the playhead follow Play
private:
    ChordariumProcessor& proc_;
    std::unique_ptr<juce::WebBrowserComponent> web_;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ChordariumEditor)
};
