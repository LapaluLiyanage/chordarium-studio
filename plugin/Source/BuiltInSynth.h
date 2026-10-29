#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace chordarium {

// Small allocation-free preview synth so Play is audible without any other instrument loaded.
// Channel 1 piano, 2 bass, 3 pad, 10 drums (same map as the MIDI export). A GM SoundFont player
// (TinySoundFont) replaces this once the SoundFont licence is confirmed (docs/decisions/licensing.md).
class BuiltInSynth {
public:
    void prepare(double sampleRate) { sr_ = sampleRate; allOff(); }
    void noteOn(int channel, int pitch, int velocity);
    void noteOff(int channel, int pitch);
    void allOff() { for (auto& v : voices_) v.active = false; }
    // Adds into left/right (does not clear them).
    void render(float* left, float* right, int numSamples);

private:
    struct Voice {
        bool active = false, released = false;
        int channel = 1, pitch = 60;
        float vel = 0, env = 0, lp = 0;
        double phase = 0, phase2 = 0, inc = 0, age = 0;
        uint64_t order = 0;
    };
    static constexpr int kVoices = 64;
    std::array<Voice, kVoices> voices_ {};
    double sr_ = 44100;
    uint64_t counter_ = 0;
    uint32_t rng_ = 22222u;
    float noise() { rng_ ^= rng_ << 13; rng_ ^= rng_ >> 17; rng_ ^= rng_ << 5; return float(rng_ & 0xFFFF) / 32768.0f - 1.0f; }
};

inline void BuiltInSynth::noteOn(int channel, int pitch, int velocity) {
    Voice* v = nullptr;
    for (auto& c : voices_) if (!c.active) { v = &c; break; }
    if (!v) { v = &voices_[0]; for (auto& c : voices_) if (c.order < v->order) v = &c; }   // steal the oldest
    *v = Voice {};
    v->active = true; v->channel = channel; v->pitch = pitch; v->vel = float(velocity) / 127.0f; v->order = ++counter_;
    v->inc = 440.0 * std::pow(2.0, (pitch - 69) / 12.0) / sr_;
}

inline void BuiltInSynth::noteOff(int channel, int pitch) {
    if (channel == 10) return;   // drums are one-shots
    for (auto& v : voices_) if (v.active && !v.released && v.channel == channel && v.pitch == pitch) v.released = true;
}

inline void BuiltInSynth::render(float* left, float* right, int n) {
    const double twoPi = 6.283185307179586;
    const float dt = float(1.0 / sr_);
    for (auto& v : voices_) {
        if (!v.active) continue;
        for (int i = 0; i < n && v.active; ++i) {
            float s = 0, pan = 0.5f;
            const float t = float(v.age); v.age += dt;
            if (v.channel == 10) {
                // drums by GM note: kick 35/36, snare 38/40, rim 37, hats 42/44/46, cymbals 49/51/52/55/57, toms otherwise
                const int p = v.pitch;
                if (p == 35 || p == 36) { v.phase += (50.f + 110.f * std::exp(-t * 28.f)) * dt; s = std::sin(float(twoPi * v.phase)) * std::exp(-t * 9.f) * 1.1f; if (t > 0.5f) v.active = false; }
                else if (p == 38 || p == 40) { v.phase += 190.0 * dt; s = (noise() * 0.7f + std::sin(float(twoPi * v.phase)) * 0.4f) * std::exp(-t * 17.f); pan = 0.45f; if (t > 0.35f) v.active = false; }
                else if (p == 37) { v.phase += 800.0 * dt; s = std::sin(float(twoPi * v.phase)) * std::exp(-t * 60.f); if (t > 0.1f) v.active = false; }
                else if (p == 42 || p == 44 || p == 46) { const float d = p == 46 ? 7.f : 38.f; const float w = noise(); s = (w - v.lp) * 0.6f * std::exp(-t * d); v.lp = w; pan = 0.6f; if (t > (p == 46 ? 0.6f : 0.15f)) v.active = false; }
                else if (p == 49 || p == 51 || p == 52 || p == 55 || p == 57) { const float w = noise(); s = (w - v.lp) * 0.5f * std::exp(-t * (p == 51 ? 4.f : 2.2f)); v.lp = w; pan = 0.65f; if (t > 1.8f) v.active = false; }
                else { v.phase += (90.f + float(p - 41) * 14.f) * dt * (1.f + 0.5f * std::exp(-t * 20.f)); s = std::sin(float(twoPi * v.phase)) * std::exp(-t * 8.f); if (t > 0.5f) v.active = false; }
                s *= v.vel * 0.55f;
            } else {
                float attack, release, decay, body;
                if (v.channel == 2) {            // bass: round, fast attack
                    attack = 400.f; release = 25.f; decay = 1.2f;
                    const float ph = float(v.phase);
                    body = 0.5f * (std::sin(float(twoPi * ph)) + 0.45f * std::sin(float(twoPi * 2 * ph)) + 0.15f * std::sin(float(twoPi * 3 * ph)));
                } else if (v.channel == 3) {     // pad: slow, slightly detuned
                    attack = 4.f; release = 3.f; decay = 0.f;
                    body = (std::sin(float(twoPi * v.phase)) + std::sin(float(twoPi * v.phase2)) + 0.3f * std::sin(float(twoPi * 2 * v.phase))) * 0.33f;
                    v.phase2 += v.inc * 1.004; if (v.phase2 >= 1.0) v.phase2 -= 1.0;
                    pan = 0.35f + 0.3f * float(v.pitch % 3) / 2.f;
                } else {                         // piano-like: bright start that decays
                    attack = 600.f; release = 12.f; decay = 1.6f;
                    const float ph = float(v.phase), br = std::exp(-t * 3.f);
                    body = 0.45f * (std::sin(float(twoPi * ph)) + 0.5f * br * std::sin(float(twoPi * 2 * ph)) + 0.25f * br * std::sin(float(twoPi * 3 * ph)) + 0.1f * br * std::sin(float(twoPi * 4 * ph)));
                    pan = 0.4f + 0.2f * float(v.pitch % 12) / 11.f;
                }
                const float target = v.released ? 0.f : 1.f, rate = target > v.env ? attack : release;
                v.env += (target - v.env) * std::min(1.f, rate * dt);
                const float amp = v.env * (decay > 0 ? std::exp(-t * decay) : 1.f);
                s = body * amp * v.vel * 0.5f;
                v.phase += v.inc; if (v.phase >= 1.0) v.phase -= 1.0;
                if ((v.released && v.env < 0.001f) || (decay > 0 && amp < 0.0005f && t > 0.05f)) v.active = false;
            }
            left[i] += s * (1.f - pan) * 1.4f;
            right[i] += s * pan * 1.4f;
        }
    }
    for (int i = 0; i < n; ++i) { left[i] = std::tanh(left[i]); right[i] = std::tanh(right[i]); }   // soft limiter
}

} // namespace chordarium
