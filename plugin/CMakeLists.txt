cmake_minimum_required(VERSION 3.25)
project(ChordariumStudio VERSION 0.1.0)
set(CMAKE_CXX_STANDARD 20)

include(FetchContent)
# [VERIFY] pin to a current JUCE 8 release tag and confirm licence tier (docs/decisions/licensing.md).
FetchContent_Declare(JUCE GIT_REPOSITORY https://github.com/juce-framework/JUCE.git GIT_TAG 8.0.4 GIT_SHALLOW ON)
FetchContent_MakeAvailable(JUCE)

juce_add_plugin(ChordariumStudio
    COMPANY_NAME "Chordarium"
    PLUGIN_MANUFACTURER_CODE Chrd   # set once, never change (spec 11.1)
    PLUGIN_CODE Chst
    FORMATS VST3 Standalone
    PRODUCT_NAME "Chordarium Studio"
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT TRUE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    NEEDS_WEB_BROWSER TRUE
    NEEDS_WEBVIEW2 TRUE
    VST3_CATEGORIES Instrument Synth)

target_sources(ChordariumStudio PRIVATE
    Source/PluginProcessor.cpp Source/PluginEditor.cpp Source/Playback.cpp Source/CoreConnection.cpp)
target_compile_definitions(ChordariumStudio PUBLIC
    JUCE_WEB_BROWSER=1 JUCE_USE_WIN_WEBVIEW2_WITH_STATIC_LINKING=1 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(ChordariumStudio PRIVATE
    juce::juce_audio_utils juce::juce_gui_extra juce::juce_audio_processors
    PUBLIC juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)

# Embed the built UI (ui/dist) so the editor needs no dev server. Run `pnpm build` in ui/ first.
file(GLOB_RECURSE CHORDARIUM_UI_FILES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../ui/dist/*")
if(CHORDARIUM_UI_FILES)
    juce_add_binary_data(ChordariumUI SOURCES ${CHORDARIUM_UI_FILES})
    target_link_libraries(ChordariumStudio PRIVATE ChordariumUI)
    target_compile_definitions(ChordariumStudio PUBLIC CHORDARIUM_EMBED_UI=1)
endif()

# Pure logic tests (no JUCE needed): tick<->PPQ and note scheduling.
add_executable(playback_tests Tests/playback_tests.cpp Source/Playback.cpp)
target_include_directories(playback_tests PRIVATE Source)
target_compile_definitions(playback_tests PRIVATE CHORDARIUM_NO_JUCE=1)
add_executable(synth_tests Tests/synth_tests.cpp)
target_include_directories(synth_tests PRIVATE Source)
enable_testing()
add_test(NAME playback COMMAND playback_tests)
add_test(NAME synth COMMAND synth_tests)
