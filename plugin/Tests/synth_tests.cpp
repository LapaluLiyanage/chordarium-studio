#include "BuiltInSynth.h"
#include <cstdio>
#include <vector>

static int failures = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL line %d: %s\n", __LINE__, #c); ++failures; } } while (0)

static float peak(const std::vector<float>& v) { float p = 0; for (float x : v) p = std::max(p, std::fabs(x)); return p; }
static bool finite(const std::vector<float>& v) { for (float x : v) if (!std::isfinite(x)) return false; return true; }

int main() {
    chordarium::BuiltInSynth s; s.prepare(44100);
    std::vector<float> l(4410, 0.f), r(4410, 0.f);

    for (int ch : { 1, 2, 3 }) {   // each pitched role is audible and bounded
        s.allOff(); std::fill(l.begin(), l.end(), 0.f); std::fill(r.begin(), r.end(), 0.f);
        s.noteOn(ch, 60, 100); s.render(l.data(), r.data(), (int) l.size());
        CHECK(finite(l) && finite(r));
        CHECK(peak(l) > 0.01f || peak(r) > 0.01f);
        CHECK(peak(l) <= 1.0f && peak(r) <= 1.0f);
    }
    for (int note : { 36, 38, 42, 46, 49, 45 }) {   // every drum voice is audible
        s.allOff(); std::fill(l.begin(), l.end(), 0.f); std::fill(r.begin(), r.end(), 0.f);
        s.noteOn(10, note, 100); s.render(l.data(), r.data(), (int) l.size());
        CHECK(finite(l) && peak(l) + peak(r) > 0.01f);
    }
    // a released note dies out
    s.allOff(); s.noteOn(2, 40, 100); s.render(l.data(), r.data(), (int) l.size()); s.noteOff(2, 40);
    for (int i = 0; i < 20; ++i) s.render(l.data(), r.data(), (int) l.size());
    std::fill(l.begin(), l.end(), 0.f); std::fill(r.begin(), r.end(), 0.f);
    s.render(l.data(), r.data(), (int) l.size());
    CHECK(peak(l) < 1e-4f);
    // 100 simultaneous notes (more than voices) stay bounded and finite
    s.allOff(); std::fill(l.begin(), l.end(), 0.f); std::fill(r.begin(), r.end(), 0.f);
    for (int i = 0; i < 100; ++i) s.noteOn(1 + (i % 3), 36 + i % 48, 127);
    s.render(l.data(), r.data(), (int) l.size());
    CHECK(finite(l) && peak(l) <= 1.0f);

    if (failures == 0) std::printf("all synth tests passed\n");
    return failures;
}
