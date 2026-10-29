#include "PluginEditor.h"
#include "CoreConnection.h"
#ifdef CHORDARIUM_EMBED_UI
#include <BinaryData.h>
#endif

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
        .withNativeFunction("previewPlay", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.previewPlay(a.size() > 2 ? double(a[2]) : 90.0); done({});   // args: sectionId, lengthQuarters, bpm
        })
        .withNativeFunction("setLoop", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.setLoop(a.size() > 0 && bool(a[0])); done({});
        })
        .withNativeFunction("setSyncMode", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.setSyncHost(a.size() > 0 && a[0].toString() == "host"); done({});
        })
        .withNativeFunction("setRoleMix", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            static const juce::StringArray roles { "piano", "bass", "pad", "drums" };
            if (a.size() > 1) { int r = roles.indexOf(a[0].toString()); if (r >= 0) proc_.setRoleMix(r, bool(a[1]["mute"]), bool(a[1]["solo"]), float(double(a[1]["gain"]))); }
            done({});
        })
        .withNativeFunction("getHostInfo", [this](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            auto* o = new juce::DynamicObject();
            o->setProperty("host", juce::PluginHostType().getHostDescription());
            o->setProperty("sampleRate", proc_.getSampleRate());
            o->setProperty("bpm", proc_.hostBpm());
            done(juce::var(o));
        })
        .withNativeFunction("reportDragRects", [](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            done({});   // [TODO M4] position native drag-handle overlays; MidiDrag.* + performExternalDragDropOfFiles (spike S3)
        })
#ifdef CHORDARIUM_EMBED_UI
        .withResourceProvider([](const juce::String& url) -> std::optional<juce::WebBrowserComponent::Resource> {
            auto name = url == "/" ? juce::String("index.html") : url.fromLastOccurrenceOf("/", false, false).upToFirstOccurrenceOf("?", false, false);
            for (int i = 0; i < BinaryData::namedResourceListSize; ++i) {
                if (juce::String(BinaryData::originalFilenames[i]) != name) continue;
                int size = 0;
                auto* data = BinaryData::getNamedResource(BinaryData::namedResourceList[i], size);
                auto ext = name.fromLastOccurrenceOf(".", false, false).toLowerCase();
                const char* mime = ext == "html" ? "text/html" : ext == "js" ? "text/javascript" : ext == "css" ? "text/css"
                                 : ext == "svg" ? "image/svg+xml" : ext == "png" ? "image/png" : ext == "woff2" ? "font/woff2" : "application/octet-stream";
                auto* bytes = reinterpret_cast<const std::byte*>(data);
                return juce::WebBrowserComponent::Resource { std::vector<std::byte>(bytes, bytes + size), mime };
            }
            return std::nullopt;
        })
#endif
        .withNativeFunction("previewStop", [this](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.previewStop(); done({});
        });
    web_ = std::make_unique<juce::WebBrowserComponent>(options);
    addAndMakeVisible(*web_);
    // [TODO M4] production: serve ui/dist via withResourceProvider; dev: Vite server below.
    web_->goToURL("http://127.0.0.1:5173/");
    setResizable(true, true);
    setResizeLimits(900, 600, 4000, 3000);
    setSize(1100, 720);
}
