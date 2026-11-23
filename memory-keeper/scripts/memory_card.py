"""Build a portable story with the originals its owner chose to share."""

from html import escape, unescape
from pathlib import Path
import json
import re
import shutil
import tempfile
import zipfile

from memory_sources import MEDIA_EXTENSIONS


LABELS = {
    "zh": ("记忆卡", "随故事保存的原件", "打开原件", "步骤", "私密版"),
    "en": ("Story card", "Originals shared with this story", "Open original", "Step", "Private edition"),
}
READER_TEXT = {
    "zh": ("分享给你的回忆", "你想问这段往事什么？", "找相关原文",
           "按词查找这份回忆录里的段落。想进一步聊，可以把这份 ZIP 和问题一起交给装了「独家记忆」 的 Codex。",
           "这份回忆录里没有找到匹配的原文。", "查看本篇素材"),
    "en": ("Memories shared with you", "What would you like to ask?", "Find passages",
           "Find matching words in these stories. For a conversation, give this ZIP and your question to Codex with Memory Keeper installed.",
           "No matching passage was found in these stories.", "See this story’s originals"),
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
h2.story-title { font: bold clamp(1.6rem,5vw,2.5rem)/1.25 Georgia,'Songti SC',SimSun,serif; color: inherit }
section { border-top: 1px solid #b9b6a8; margin-top: 1.8rem; padding-top: .5rem }
figure { margin: .9rem 0; background: #eeeade; padding: 1rem; border-radius: .35rem }
figcaption { margin-bottom: .6rem }
img, video { max-width: 100%; max-height: 28rem; display: block; margin-bottom: .5rem }
audio { width: 100%; display: block; margin-bottom: .4rem }
a { text-underline-offset: .2em }
form { padding: 1rem 0; border-block: 1px solid #b9b6a8 }
label { display: block; font-weight: bold }
.controls { display: flex; flex-wrap: wrap; gap: .5rem; margin: .5rem 0 }
input, button { font: inherit; padding: .45rem .7rem; border: 1px solid #66786c; border-radius: .3rem }
input { min-width: 0; flex: 1 1 12rem }
button { color: white; background: #355148; cursor: pointer }
form small { display: block; line-height: 1.55 }
#matches p { margin: .4rem 0 }
[id]:target { outline: 2px solid #af613d; outline-offset: .25rem }
@media(max-width: 48rem) { main { margin: 0 auto; min-height: 100vh } }
@media print { body, main, figure { background: white } main { margin: 0 } audio, video, a, form { display: none } }
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


def selected_assets(vault, stories, selected):
    paths = dict.fromkeys(selected)
    if paths.keys() - {ref["path"] for story in stories for ref in story["refs"]}:
        raise ValueError("choose originals listed by the media command for the selected stories")
    assets = {}
    for number, path in enumerate(paths, start=1):
        source = vault / path
        if source.suffix[1:] not in MEDIA_EXTENSIONS:
            raise ValueError(f"unsupported original format: {source.suffix}")
        if not source.is_file() or source.resolve().parent != (vault.resolve() / "media"):
            raise ValueError(f"original missing from the vault: {path}")
        assets[path] = f"media/{number}{source.suffix}"
    return assets


def render_story(story, key, assets, lang, single, after_header):
    _, collection, original, step_label, edition = LABELS[lang]
    passages, originals = [], []

    def anchor(match):
        tag, content = match.groups()
        mark = f"{key}-p{len(passages) + 1}"
        text = unescape(re.sub(r"<[^>]+>", "", content))
        passages.append({"anchor": mark, "text": text, "kind": "quotation" if tag == "blockquote" else "passage"})
        return f'<{tag} id="{mark}" data-passage>{content}</{tag}>'

    body = re.sub(r"<(p|blockquote|li)>(.*?)</\1>", anchor, story["html"], flags=re.S)
    figures = []
    for ref in story["refs"]:
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
        mark = f"{key}-m{len(originals) + 1}"
        originals.append({**{k: ref[k] for k in ("name", "step", "at") if k in ref}, "file": link, "anchor": mark})
        figures.append(f'<figure id="{mark}"><figcaption>{" · ".join(caption)}</figcaption>{player}'
                       f'<a href="{link}">{original}</a></figure>')
    gallery = f'<section id="{key}-media"><h2>{collection}</h2>{"".join(figures)}</section>' if figures else ""
    title, context = story["title"], story["context"]
    entry = {"id": key, "title": title, "context": context, "passages": passages, "media": originals}
    heading = "h1" if single else "h2"
    details = f'<p class="meta">{escape(context)}</p>' if context else ""
    marker = f'<p class="meta">{edition}</p>' if story["private"] and not single else ''
    html = (f'<article id="{key}"><header><{heading} class="story-title">{escape(title)}</{heading}>'
            f'{details}{marker}</header>{after_header}{body}{gallery}</article>')
    return html, entry


def build_card(vault, stories, lang, selected):
    kind, _, _, _, edition = LABELS[lang]
    memoir, question, find, hint, empty, originals = READER_TEXT[lang]
    assets = selected_assets(vault, stories, selected)
    single = len(stories) == 1
    private = any(s["private"] for s in stories)
    title = stories[0]["title"] if single else memoir
    form = (f'<form id="ask" data-empty="{empty}" data-originals="{originals}"><label for="q">{question}</label>'
            f'<div class="controls"><input id="q" type="search" required><button>{find}</button></div>'
            f'<small>{hint}</small><div id="matches" aria-live="polite"></div></form>')
    sections, entries = [], []
    for number, story in enumerate(stories, start=1):
        html, entry = render_story(story, f"s{number}", assets, lang, single, form if single else "")
        sections.append(html)
        entries.append(entry)
    manifest = {"format": "memory-keeper-share-v1", "stories": entries}
    reader = Path(__file__).with_name("card_reader.js").read_text(encoding="utf-8")
    marker = f" · {edition}" if private else ""
    contents = "".join(sections)
    if not single:
        contents = f"<h1>{memoir}</h1>{form}" + contents
    page = (f'<!doctype html>\n<html lang="{"zh-CN" if lang == "zh" else "en"}"><head>'
            f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{CSS}</style></head><body><main>'
            f'<p class="meta">{"独家记忆" if lang == "zh" else "Memory Keeper"} · {kind}{marker}</p>{contents}</main>'
            f'<script>{reader}</script></body></html>\n')

    folder = vault / "exports"
    folder.mkdir(exist_ok=True)
    stem = stories[0]["stem"] if single else ("我的回忆" if lang == "zh" else "My memories")
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
            bundle.writestr(zipfile.ZipInfo("stories.json"), json.dumps(manifest, ensure_ascii=False, indent=2).encode(), zipfile.ZIP_DEFLATED)
            for path, link in assets.items():
                info = zipfile.ZipInfo(link)
                if link.endswith(".wav"):
                    info.compress_type = zipfile.ZIP_DEFLATED
                with (vault / path).open("rb") as source, bundle.open(info, "w", force_zip64=True) as dest:
                    shutil.copyfileobj(source, dest, 1024 * 1024)
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    return {"written": target.as_posix(), "stories": len(stories), "originals": len(assets), "private": private}


def read_share(path, story_id):
    """Read only the supplied package, including when the recipient has no vault."""
    path = Path(path).expanduser()
    if path.is_dir():
        path = path / "stories.json"
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as bundle:
                data = json.loads(bundle.read("stories.json"))
        except KeyError:
            raise ValueError("older card: open index.html and use its visible story as the source") from None
        except zipfile.BadZipFile as exc:
            raise ValueError("invalid ZIP") from exc
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("format") != "memory-keeper-share-v1" or not isinstance(data.get("stories"), list):
        raise ValueError("expected a Memory Keeper shared memoir")
    for s in data["stories"]:
        if (not isinstance(s, dict) or not all(isinstance(s.get(k), str) for k in ("id", "title", "context"))
                or not isinstance(s.get("passages"), list) or not isinstance(s.get("media"), list)):
            raise ValueError("invalid story in shared memoir")
    if story_id is None:
        return {"stories": [{k: s[k] for k in ("id", "title", "context")} for s in data["stories"]]}
    for story in data["stories"]:
        if story["id"] == story_id:
            return story
    raise ValueError(f"unknown shared story: {story_id}")
