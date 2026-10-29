#include "CoreConnection.h"

static juce::File dataDir() {
    return juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory).getChildFile("ChordariumStudio");
}

CoreConnection::Info CoreConnection::discover() {
    int port = 47811;
    auto cfg = juce::JSON::parse(dataDir().getChildFile("config.json"));
    if (cfg.hasProperty("port")) port = int(cfg["port"]);
    return { "http://127.0.0.1:" + juce::String(port), dataDir().getChildFile("token").loadFileAsString().trim() };
}

bool CoreConnection::isHealthy(const Info& i) {
    juce::URL url(i.baseUrl + "/health");
    if (auto s = url.createInputStream(juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress).withConnectionTimeoutMs(800)))
        return s->readEntireStreamAsString().contains("\"ok\"");
    return false;
}

juce::File CoreConnection::exportPart(const Info& i, const juce::String& partId) {
    // "section:<id>" exports every part of that section as one multi-track .mid; anything else is a single part.
    const bool wholeSection = partId.startsWith("section:");
    auto* ids = new juce::DynamicObject();
    ids->setProperty("scope", wholeSection ? "section" : "part");
    ids->setProperty("ids", juce::Array<juce::var>{ wholeSection ? partId.fromFirstOccurrenceOf("section:", false, false) : partId });
    auto url = juce::URL(i.baseUrl + "/export").withPOSTData(juce::JSON::toString(juce::var(ids), true));
    auto opts = juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inPostData).withConnectionTimeoutMs(3000)
        .withExtraHeaders("Content-Type: application/json\r\nX-Chordarium-Token: " + i.token)
        .withHttpRequestCmd("POST");
    if (auto s = url.createInputStream(opts)) {
        auto files = juce::JSON::parse(s->readEntireStreamAsString())["files"];
        if (files.isArray() && files.size() > 0) return juce::File(files[0].toString());
    }
    return {};
}

static const char* kAuthJson = "Content-Type: application/json\r\nX-Chordarium-Token: ";

juce::String CoreConnection::getSnapshot(const Info& i) {
    juce::URL url(i.baseUrl + "/session/snapshot");
    if (auto s = url.createInputStream(juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
            .withConnectionTimeoutMs(800).withExtraHeaders(juce::String(kAuthJson) + i.token)))
        return s->readEntireStreamAsString();
    return {};
}

bool CoreConnection::putSnapshot(const Info& i, const juce::String& json) {
    auto url = juce::URL(i.baseUrl + "/session/snapshot").withPOSTData(json);
    int status = 0;
    auto opts = juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inPostData).withConnectionTimeoutMs(3000)
        .withExtraHeaders(juce::String(kAuthJson) + i.token).withHttpRequestCmd("PUT").withStatusCode(&status);
    if (auto s = url.createInputStream(opts)) { s->readEntireStreamAsString(); return status >= 200 && status < 300; }
    return false;
}

bool CoreConnection::newSession(const Info& i) {
    auto url = juce::URL(i.baseUrl + "/session/new").withPOSTData("{}");
    int status = 0;
    auto opts = juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inPostData).withConnectionTimeoutMs(3000)
        .withExtraHeaders(juce::String(kAuthJson) + i.token).withHttpRequestCmd("POST").withStatusCode(&status);
    if (auto s = url.createInputStream(opts)) { s->readEntireStreamAsString(); return status >= 200 && status < 300; }
    return false;
}

bool CoreConnection::startCoreIfNeeded() {
    if (isHealthy(discover())) return true;
    // [VERIFY] install path comes from the installer; this default matches installer/ChordariumStudio.iss
    juce::File exe("C:\\Program Files\\Chordarium Studio\\chordarium-core.exe");
    if (!exe.existsAsFile()) return false;
    return exe.startAsProcess();
}
