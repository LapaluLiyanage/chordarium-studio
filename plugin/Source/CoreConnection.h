#pragma once
#include <juce_core/juce_core.h>

// Reads port + token from %APPDATA%/ChordariumStudio and checks /health. Never stores secrets in plugin state.
class CoreConnection {
public:
    struct Info { juce::String baseUrl; juce::String token; };
    static Info discover();                 // port from config.json (default 47811), token from the token file
    static bool isHealthy(const Info&);     // GET /health, 127.0.0.1 only
    static bool startCoreIfNeeded();        // launches chordarium-core.exe from the install dir if /health fails
};
