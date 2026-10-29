#pragma once
#include <juce_core/juce_core.h>

// Reads port + token from %APPDATA%/ChordariumStudio and checks /health. Never stores secrets in plugin state.
class CoreConnection {
public:
    struct Info { juce::String baseUrl; juce::String token; };
    static Info discover();                 // port from config.json (default 47811), token from the token file
    static bool isHealthy(const Info&);     // GET /health, 127.0.0.1 only
    static juce::File exportPart(const Info&, const juce::String& partId);   // POST /export {scope:part}; empty File on failure
    static juce::String getSnapshot(const Info&);                        // GET /session/snapshot as JSON text, empty on failure
    static bool putSnapshot(const Info&, const juce::String& json);     // PUT /session/snapshot (restore after a project reload)
    static bool startCoreIfNeeded();        // launches chordarium-core.exe from the install dir if /health fails
};
