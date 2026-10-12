"""Procedurally generated sounds (no asset files needed).

The famous Sidewinder "growl": a low buzzing tone while the seeker searches,
switching to a high pitched steady tone when a heat source is in the seeker
(or locked).  The RWR beeps for new emitters, beeps steadily for a lock and
warbles fast for a missile launch.
"""

import math
import os
import random
import struct
import tempfile
import wave

RATE = 22050
CACHE_VERSION = 2


def _write(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000)) for s in samples))


def _growl(n):
    out = []
    for i in range(n):
        t = i / RATE
        am = 0.55 + 0.45 * math.sin(2 * math.pi * 20 * t)
        s = (math.sin(2 * math.pi * 400 * t) + 0.5 * math.sin(2 * math.pi * 800 * t)
             + 0.25 * math.sin(2 * math.pi * 1200 * t))
        out.append(0.35 * am * s)
    return out


def _tone(n, freq, vib=0.0):
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = freq * (1.0 + vib * math.sin(2 * math.pi * 6 * t))
        phase += 2 * math.pi * f / RATE
        out.append(0.4 * math.sin(phase))
    return out


def _beeps(n, freq, rate_hz, duty=0.5):
    out = []
    for i in range(n):
        t = i / RATE
        on = (t * rate_hz) % 1.0 < duty
        out.append(0.4 * math.sin(2 * math.pi * freq * t) if on else 0.0)
    return out


def _warble(n):
    out = []
    for i in range(n):
        t = i / RATE
        f = 1400 if int(t * 16) % 2 == 0 else 950
        out.append(0.4 * math.sin(2 * math.pi * f * t))
    return out


def _noise(n, rnd, lowpass=0.1, gain=1.0, envelope=None, pulse_hz=0.0):
    out = []
    y = 0.0
    for i in range(n):
        x = rnd.uniform(-1.0, 1.0)
        y += lowpass * (x - y)
        s = y * gain
        if pulse_hz:
            s *= 0.4 + 0.6 * max(0.0, math.sin(2 * math.pi * pulse_hz * i / RATE))
        if envelope is not None:
            s *= envelope(i / n)
        out.append(s)
    return out


def generate(directory):
    rnd = random.Random(42)
    sounds = {
        "growl": lambda: _growl(RATE),
        "lock_tone": lambda: _tone(RATE, 1150.0, vib=0.004),
        "rwr_new": lambda: _beeps(int(RATE * 0.36), 1800.0, 6.0, 0.5),
        "rwr_lock": lambda: _beeps(RATE, 1000.0, 4.0, 0.5),
        "rwr_launch": lambda: _warble(RATE),
        "gun": lambda: _noise(RATE, rnd, lowpass=0.35, gain=2.2, pulse_hz=100.0),
        "engine": lambda: _noise(RATE * 2, rnd, lowpass=0.04, gain=6.0),
        "afterburner": lambda: _noise(RATE * 2, rnd, lowpass=0.12, gain=3.0),
        "launch": lambda: _noise(int(RATE * 1.4), rnd, lowpass=0.2, gain=2.5,
                                 envelope=lambda u: min(1.0, u * 20.0) * (1.0 - u) ** 1.5),
        "explosion": lambda: _noise(int(RATE * 2.0), rnd, lowpass=0.03, gain=9.0,
                                    envelope=lambda u: min(1.0, u * 50.0) * (1.0 - u) ** 2.5),
        "hit": lambda: _noise(int(RATE * 0.12), rnd, lowpass=0.5, gain=1.5, envelope=lambda u: (1.0 - u) ** 2),
    }
    paths = {}
    for name, make in sounds.items():
        path = os.path.join(directory, name + ".wav")
        if not os.path.exists(path):
            _write(path, make())
        paths[name] = path
    return paths


class SoundBank:
    LOOPS = ("growl", "lock_tone", "rwr_lock", "rwr_launch", "gun", "engine", "afterburner")

    def __init__(self, base, volume=0.8, enabled=True):
        self.base = base
        self.volume = volume
        self.enabled = enabled
        self.sounds = {}
        self._playing = set()
        if not enabled:
            return
        directory = os.path.join(tempfile.gettempdir(), "dogfight_sounds_v%d" % CACHE_VERSION)
        os.makedirs(directory, exist_ok=True)
        for name, path in generate(directory).items():
            snd = base.loader.loadSfx(path)
            if name in self.LOOPS:
                snd.setLoop(True)
            self.sounds[name] = snd

    def _loop(self, name, on, volume=1.0, rate=1.0):
        snd = self.sounds.get(name)
        if snd is None:
            return
        if on:
            snd.setVolume(volume * self.volume)
            snd.setPlayRate(rate)
            if name not in self._playing:
                snd.play()
                self._playing.add(name)
        elif name in self._playing:
            snd.stop()
            self._playing.discard(name)

    def play(self, name, volume=1.0):
        snd = self.sounds.get(name)
        if snd is not None:
            snd.setVolume(volume * self.volume)
            snd.play()

    def stop_all(self):
        for name in list(self._playing):
            self._loop(name, False)

    def handle_event(self, kind, data, player):
        if not self.enabled or player is None:
            return
        if kind == "launch" and data.get("shooter") is player:
            self.play("launch", 0.8)
        elif kind == "explosion":
            dist = (data["pos"] - player.pos).length()
            if dist < 12000.0:
                self.play("explosion", max(0.15, 1.0 - dist / 12000.0))
        elif kind == "hit" and (data.get("target") is player or data.get("shooter") is player):
            self.play("hit", 0.7)

    def update(self, player, paused=False):
        if not self.enabled:
            return
        if player is None or not player.alive or paused:
            self.stop_all()
            return
        engine = player.fm.engine
        self._loop("engine", True, 0.35 + 0.3 * min(engine, 1.0), 0.7 + 0.5 * min(engine, 1.0))
        self._loop("afterburner", engine > 1.0, 0.5)
        self._loop("gun", player.gun.firing, 0.8)
        spec = player.selected_spec
        ir = spec is not None and spec.guidance == "IR"
        tone = player.ir_seeker.tone() if ir else "none"
        self._loop("growl", tone == "growl", 0.25)
        self._loop("lock_tone", tone == "lock", 0.3)
        level = player.rwr.max_level
        near = player.rwr.incoming[0][0] if player.rwr.incoming else 1e9
        self._loop("rwr_launch", level >= 3, 0.45, 1.0 + 0.8 * max(0.0, min(1.0, (8000.0 - near) / 8000.0)))
        self._loop("rwr_lock", level == 2, 0.35)
        if player.rwr.new_search:
            self.play("rwr_new", 0.35)
