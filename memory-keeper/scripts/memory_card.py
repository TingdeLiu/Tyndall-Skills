"""Build a portable story with the originals its owner chose to share."""

from html import escape
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from memory_sources import MEDIA_EXTENSIONS


LABELS = {
    "zh": ("家庭记忆卡", "随故事保存的原件", "打开原件", "步骤", "私密版"),
    "en": ("Family story card", "From the family archive", "Open original", "Step", "Private edition"),
}
IMAGE = set("jpg jpeg jfif png gif webp avif bmp".split())
AUDIO = set("wav mp3 m4a aac flac ogg oga opus".split())
VIDEO = set("mp4 m4v mov webm ogv".split())
CSS = """
* { box-sizing: border-box }
html { color-scheme: light }
body { margin: 0; color: #2c332f; background: #f1eee6;
  font: 18px/1.75 'STIX Two Text', Georgia, 'Songti SC', SimSun, serif }
main { max-width: 44rem; margin: 3rem auto; padding: clamp(1.4rem, 6vw, 4rem);
  background: #fffdf6; border-top: .4rem solid #355148; overflow-wrap: anywhere }
header { border-bottom: 1px solid #b9b6a8; margin-bottom: 1.6rem; padding-bottom: 1rem }
header p, figcaption, a, h2, .meta { font: 600 .85rem/1.6 'Atkinson Hyperlegible Next',
  system-ui, sans-serif; color: #42564c }
header p { margin: 0 }
h1 { font-size: clamp(2.1rem, 7vw, 3.8rem); line-height: 1.14; margin: .6em 0 .32em }
blockquote { border-left: 3px solid #af613d; padding-left: 1.1em; margin: 1rem 0; color: #764627 }
h4 { font-size: 1rem; margin: 1.2rem 0 .4rem }
section { border-top: 1px solid #b9b6a8; margin-top: 1.8rem; padding-top: .5rem }
figure { margin: .9rem 0; background: #eeeade; padding: 1rem; border-radius: .35rem }
figcaption { margin-bottom: .6rem }
img, video { max-width: 100%; max-height: 28rem; display: block; margin-bottom: .5rem }
audio { width: 100%; display: block; margin-bottom: .4rem }
a { text-underline-offset: .2em }
@media(max-width: 48rem) { main { margin: 0 auto; min-height: 100vh } }
@media print { body, main, figure { background: white } main { margin: 0 } audio, video, a { display: none } }
"""


def time_fragment(at):
    if not at:
        return ""
    seconds = []
    for stamp in re.split(r"\s*[-–]\s*", at):
        clock, separator, fraction = stamp.partition(".")
        value = 0
        for part in clock.split(":"):
            value = value * 60 + int(part)
        seconds.append(f"{value}{separator}{fraction}")
    return "#t=" + ",".join(seconds)


def build_card(vault, stem, title, context, story_html, lang, private, refs, selected):
    kind, collection, original, step_label, edition = LABELS[lang]
    paths = dict.fromkeys(selected)
    if paths.keys() - {ref["path"] for ref in refs}:
        raise ValueError("choose original paths listed for this story by the media command")
    assets = {}
    for number, path in enumerate(paths, start=1):
        source = vault / path
        if source.suffix[1:] not in MEDIA_EXTENSIONS:
            raise ValueError(f"unsupported original format: {source.suffix}")
        if not source.is_file() or source.resolve().parent != (vault.resolve() / "media"):
            raise ValueError(f"original missing from the vault: {path}")
        assets[path] = f"media/{number}{source.suffix}"

    figures = []
    for ref in refs:
        link = assets.get(ref["path"])
        if not link:
            continue
        name = escape(ref["name"])
        at = ref.get("at", "")
        caption = [name]
        if "step" in ref:
            caption.append(f"{step_label} {ref['step']}")
        if at:
            caption.append(escape(at))
        ext = Path(link).suffix[1:]
        player = ""
        if ext in IMAGE:
            player = f'<img src="{link}" alt="{name}" loading="lazy">'
        elif ext in AUDIO or ext in VIDEO:
            tag = "audio" if ext in AUDIO else "video"
            player = f'<{tag} controls preload="metadata" src="{link}{time_fragment(at)}"></{tag}>'
        figures.append(f'<figure><figcaption>{" · ".join(caption)}</figcaption>{player}'
                       f'<a href="{link}">{original}</a></figure>')
    gallery = f'<section><h2>{collection}</h2>{"".join(figures)}</section>' if figures else ""
    marker = f" · {edition}" if private else ""
    details = f'<p class="meta">{escape(context)}</p>' if context else ""
    page = (f'<!doctype html>\n<html lang="{"zh-CN" if lang == "zh" else "en"}"><head>'
            f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{CSS}</style></head><body><main>'
            f'<header><p>Memory Keeper · {kind}{marker}</p><h1>{escape(title)}</h1>{details}</header>'
            f'<article>{story_html}</article>{gallery}</main></body></html>\n')

    folder = vault / "exports"
    folder.mkdir(exist_ok=True)
    basename = f"{stem}-{'记忆卡' if lang == 'zh' else 'card'}" + (f"-{edition}" if private else "")
    target = folder / f"{basename}.zip"
    version = 1
    while target.exists():
        version += 1
        target = folder / f"{basename}-{version}.zip"
    with tempfile.NamedTemporaryFile(dir=folder, delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        with zipfile.ZipFile(staged, "w") as bundle:
            bundle.writestr(zipfile.ZipInfo("index.html"), page.encode("utf-8"), zipfile.ZIP_DEFLATED)
            for path, link in assets.items():
                info = zipfile.ZipInfo(link)
                if link.endswith(".wav"):
                    info.compress_type = zipfile.ZIP_DEFLATED
                with (vault / path).open("rb") as source, bundle.open(info, "w", force_zip64=True) as dest:
                    shutil.copyfileobj(source, dest, 1024 * 1024)
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    return {"written": target.as_posix(), "originals": len(assets), "private": private}
