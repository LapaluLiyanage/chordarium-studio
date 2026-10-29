#include "PluginEditor.h"
#include "CoreConnection.h"
#ifdef CHORDARIUM_EMBED_UI
#include <BinaryData.h>
#endif

ChordariumEditor::~ChordariumEditor() = default;

void ChordariumEditor::timerCallback() {
    if (!web_) return;
    auto* o = new juce::DynamicObject();
    o->setProperty("playing", proc_.shownPlaying());
    o->setProperty("quarters", proc_.shownQuarters());
    o->setProperty("bpm", proc_.hostBpm());
    web_->emitEventIfBrowserIsVisible("transport", juce::var(o));
}

ChordariumEditor::ChordariumEditor(ChordariumProcessor& p) : AudioProcessorEditor(&p), proc_(p) {
    CoreConnection::startCoreIfNeeded();
    auto info = CoreConnection::discover();
    // Project reopened: push the saved session back into core so the UI shows the same song and parts.
    if (proc_.takeNeedsRestore()) CoreConnection::putSnapshot(info, proc_.snapshot());
    else if (!proc_.sessionInitialised()) CoreConnection::newSession(info);   // brand-new instance: do not show the previous project's song
    proc_.markSessionInitialised();
    auto options = juce::WebBrowserComponent::Options()
        .withBackend(juce::WebBrowserComponent::Options::Backend::webview2)
        // Hosts such as Cubase live in a read-only Program Files folder, so WebView2 needs its own writable data folder.
        .withWinWebView2Options(juce::WebBrowserComponent::Options::WinWebView2{}
            .withUserDataFolder(juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory).getChildFile("ChordariumStudio").getChildFile("webview2")))
        .withNativeIntegrationEnabled()
        .withNativeFunction("getCoreConnection", [info](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            auto* o = new juce::DynamicObject();
            o->setProperty("baseUrl", info.baseUrl);
            o->setProperty("token", info.token);
            done(juce::var(o));
        })
        .withNativeFunction("previewPlay", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            // args: sectionId, lengthQuarters, bpm. Pull this section's notes from core, then start the preview.
            const auto sectionId = a.size() > 0 ? a[0].toString() : juce::String();
            const double lengthQ = a.size() > 1 ? double(a[1]) : 16.0;
            const double bpm = a.size() > 2 ? double(a[2]) : 90.0;
            auto snap = juce::JSON::parse(CoreConnection::getSnapshot(CoreConnection::discover()));
            std::vector<chordarium::Note> notes;
            if (auto* parts = snap["parts"].getDynamicObject())
                for (auto& prop : parts->getProperties()) {
                    auto& part = prop.value;
                    if (part["section_id"].toString() != sectionId) continue;
                    const int channel = int(part["channel"]);
                    if (auto* list = part["notes"].getArray())
                        for (auto& n : *list)
                            notes.push_back({ int(n["pitch"]), int64_t(n["start"]), int64_t(n["duration"]), int(n["velocity"]), channel });
                }
            proc_.setNotes(std::move(notes), int64_t(lengthQ * chordarium::kPPQ));
            proc_.previewPlay(bpm); done({});
        })
        .withNativeFunction("setBuiltInSound", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.setBuiltInSound(a.size() > 0 && bool(a[0])); done({});
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
            o->setProperty("builtInSound", proc_.builtInSound());
            done(juce::var(o));
        })
        .withNativeFunction("reportDragRects", [](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            juce::ignoreUnused(a);   // drag handles are handled by the page itself now (startFileDrag)
            done({});
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
        .withNativeFunction("startFileDrag", [](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            // Called while the mouse button is still down. "section:<id>" exports every part as one multi-track file.
            juce::String path;
            if (a.size() > 0) {
                auto file = CoreConnection::exportPart(CoreConnection::discover(), a[0].toString());
                if (file.existsAsFile()) {
                    path = file.getFullPathName();
                    juce::DragAndDropContainer::performExternalDragDropOfFiles({ path }, false, nullptr);   // OS drag runs on JUCE's own thread
                }
            }
            done(path);
        })
        .withNativeFunction("revealFile", [](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            if (a.size() > 0) { juce::File f(a[0].toString()); if (f.exists()) f.revealToUser(); }
            done({});
        })
        .withNativeFunction("previewStop", [this](const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            proc_.previewStop(); done({});
        });
    web_ = std::make_unique<juce::WebBrowserComponent>(options);
    addAndMakeVisible(*web_);
#ifdef CHORDARIUM_EMBED_UI
    web_->goToURL(juce::WebBrowserComponent::getResourceProviderRoot());
#else
    web_->goToURL("http://127.0.0.1:5173/");   // dev: Vite server
#endif
    startTimerHz(30);
    setResizable(true, true);
    setResizeLimits(900, 600, 4000, 3000);
    setSize(1100, 720);
}
