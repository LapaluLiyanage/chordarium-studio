#include "PluginEditor.h"
#include "CoreConnection.h"

ChordariumEditor::ChordariumEditor(ChordariumProcessor& p) : AudioProcessorEditor(&p), proc_(p) {
    CoreConnection::startCoreIfNeeded();
    auto info = CoreConnection::discover();
    auto options = juce::WebBrowserComponent::Options()
        .withBackend(juce::WebBrowserComponent::Options::Backend::webview2)
        .withNativeIntegrationEnabled()
        .withNativeFunction("getCoreConnection", [info](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            auto* o = new juce::DynamicObject();
            o->setProperty("baseUrl", info.baseUrl);
            o->setProperty("token", info.token);
            done(juce::var(o));
        })
        .withNativeFunction("previewStop", [this](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.previewStop(); done({});
        });
    // [TODO M4] previewPlay, setRoleMix, setSyncMode, reportDragRects, getHostInfo; serve the built ui/dist via withResourceProvider.
    web_ = std::make_unique<juce::WebBrowserComponent>(options);
    addAndMakeVisible(*web_);
    web_->goToURL("http://127.0.0.1:5173/");   // dev server; production uses the resource provider root
    setResizable(true, true);
    setResizeLimits(900, 600, 4000, 3000);
    setSize(1100, 720);
}
