#pragma once
#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

// WebView host. [VERIFY] exact JUCE 8 WebBrowserComponent::Options API (withNativeIntegrationEnabled,
// withResourceProvider, withNativeFunction, emitEventIfBrowserIsVisible) against the JUCE 8 docs before M4 sign-off.
class ChordariumEditor : public juce::AudioProcessorEditor {
public:
    explicit ChordariumEditor(ChordariumProcessor&);
    void resized() override { web_->setBounds(getLocalBounds()); }
private:
    ChordariumProcessor& proc_;
    std::unique_ptr<juce::WebBrowserComponent> web_;
};
