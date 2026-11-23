"""Rebuild the two public demo ZIPs from fictional stories and synthesized sound."""

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "scripts" / "memory_vault.py"
STORIES = {
    "zh": ("外公的敲门声", "我", "小时候的周末", "敲门暗号.wav",
           "外公来我家，总是轻轻敲两下，停一下，再敲重重的一下。我在屋里听见，连猫眼都不用看。",
           "我妈问我怎么知道是他。我说，别人都按门铃。", "虚构故事 · 音效为合成示例"),
    "en": ("Grandpa’s knock", "me", "Weekends when I was little", "The door knock.wav",
           "Grandpa always knocked twice, waited, then knocked once more, louder. I could tell it was him without looking through the peephole.",
           "Mum asked how I knew. I told her everyone else rang the bell.", "Fictional story · synthesized audio"),
}


def make_knocks(path):
    rate = 16000
    samples = bytearray()
    for index in range(3 * rate):
        time = index / rate
        signal = 0.0
        for onset, volume in [(0.35, 0.55), (0.64, 0.55), (1.65, 1.0)]:
            t = time - onset
            if 0 <= t < 0.45:
                signal += volume * (1 - math.exp(-t * 1200)) * math.exp(-t * 26) * (
                    .65 * math.sin(2 * math.pi * 134 * t) + .25 * math.sin(2 * math.pi * 372 * t))
        samples.extend(struct.pack("<h", round(signal * 30000)))
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(samples)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        env = dict(os.environ, MEMORY_KEEPER_CONFIG=str(root / "config.json"))

        def cli(*args, draft=None):
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CLI), *map(str, args)],
                                    input=draft, encoding="utf-8", capture_output=True, env=env)
            if result.returncode:
                raise RuntimeError(result.stderr)
            return json.loads(result.stdout)

        make_knocks(HERE / "knock.wav")
        for lang, (title, narrator, when, filename, story, quote, note) in STORIES.items():
            cli("init", root / lang, "--language", lang)
            audio = root / filename
            shutil.copyfile(HERE / "knock.wav", audio)
            draft = (f"---\ntype: memory\ntitle: {title}\nnarrator: {narrator}\nevent_date: {when}\n"
                     f"summary: {title}\n---\n\n{story}\n\n> {quote}\n\n{note}\n")
            memory = cli("add", "-", "--attach", audio, draft=draft)
            media = cli("media", memory["id"])["media"][0]["path"]
            card = cli("card", memory["id"], "--media", media)
            shutil.copyfile(card["written"], HERE / f"knock-{lang}.zip")


if __name__ == "__main__":
    main()
