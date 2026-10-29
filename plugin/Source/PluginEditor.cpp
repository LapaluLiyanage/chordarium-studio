#include "PluginEditor.h"
#include "CoreConnection.h"
#ifdef CHORDARIUM_EMBED_UI
#include <BinaryData.h>
#endif

// Transparent overlay over a part row's name column. Dragging it exports the part to a .mid and starts an
// external file drag (spike S3: confirm Cubase accepts the drop). A plain click falls through to the UI.
class DragHandle : public juce::Component {
public:
    DragHandle(ChordariumEditor& e, juce::String id) : editor_(e), partId_(std::move(id)) { setMouseCursor(juce::MouseCursor::DraggingHandCursor); }
    void mouseDrag(const juce::MouseEvent& ev) override {
        if (started_ || ev.getDistanceFromDragStart() < 6) return;
        started_ = true;
        auto file = CoreConnection::exportPart(CoreConnection::discover(), partId_);
        if (file.existsAsFile())
            juce::DragAndDropContainer::performExternalDragDropOfFiles({ file.getFullPathName() }, false, this);
    }
    void mouseUp(const juce::MouseEvent&) override { started_ = false; }
private:
    ChordariumEditor& editor_;
    juce::String partId_;
    bool started_ = false;
};

ChordariumEditor::~ChordariumEditor() = default;

void ChordariumEditor::setDragRects(const juce::Array<juce::var>& rects) {
    handles_.clear(); handleIds_.clear(); handleRects_.clear();
    for (auto& r : rects) {
        handleIds_.add(r["partId"].toString());
        handleRects_.add({ int(double(r["x"])), int(double(r["y"])), int(double(r["w"])), int(double(r["h"])) });
        auto* h = handles_.add(new DragHandle(*this, handleIds_.getReference(handleIds_.size() - 1)));
        addAndMakeVisible(h);
    }
    layoutHandles();
}

void ChordariumEditor::layoutHandles() {
    for (int i = 0; i < handles_.size(); ++i) {
        auto r = handleRects_[i];   // handle covers the lane's name column only (96 px), leaving the piano roll clickable
        handles_[i]->setBounds(r.getX(), r.getY(), juce::jmin(96, r.getWidth()), r.getHeight());
        handles_[i]->toFront(false);
    }
}

ChordariumEditor::ChordariumEditor(ChordariumProcessor& p) : AudioProcessorEditor(&p), proc_(p) {
    CoreConnection::startCoreIfNeeded();
    auto info = CoreConnection::discover();
    // Project reopened: push the saved session back into core so the UI shows the same song and parts.
    if (proc_.takeNeedsRestore()) CoreConnection::putSnapshot(info, proc_.snapshot());
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
        .withNativeFunction("reportDragRects", [this](const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done) {
            if (a.size() > 0 && a[0].isArray()) setDragRects(*a[0].getArray());
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
