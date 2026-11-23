"""Local originals and resumable interviews. Text entries remain ordinary Markdown."""

import hashlib
import json
import os
import re
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path


MEDIA_EXTENSIONS = set("""
    jpg jpeg jfif png gif webp heic heif avif tif tiff bmp dng cr2 cr3 nef arw raf
    wav mp3 m4a aac aif aiff caf flac ogg oga opus amr awb wma silk
    mp4 m4v mov mkv avi webm 3gp 3g2 mts m2ts mpg mpeg wmv ogv
""".split())
SOURCE_HEADINGS = {"## 原始素材", "## Original sources"}
TIME = r"(?:\d+:)?\d+:[0-5]\d(?:\.\d+)?"
TIME_RANGE = rf"{TIME}(?:\s*[-–]\s*{TIME})?"
MEDIA_LINK = re.compile(r"^- \[(.*?)\]\(\.\./(media/[0-9a-f]{64}\.[a-z0-9]+)\)"
                        rf"(?: · (?:步骤 |Step )(\d+))?(?: · ({TIME_RANGE}))?$")


@contextmanager
def vault_lock(vault):
    """OS releases this lock even if a writer exits during an import."""
    with (vault / ".memory-keeper.lock").open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def atomic_bytes(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        staged = Path(tmp.name)
        try:
            tmp.write(data)
            tmp.close()
            if path.exists():
                os.chmod(staged, path.stat().st_mode)
            os.replace(staged, path)
        finally:
            tmp.close()
            staged.unlink(missing_ok=True)


def media_inputs(names):
    files = [Path(name).expanduser() for name in names]
    for file in files:
        if not file.is_file() or file.suffix.lower()[1:] not in MEDIA_EXTENSIONS:
            raise ValueError(f"expected a local audio, image or video file: {file}")
    return files


def archive_media(vault, files):
    refs = []
    if not files:
        return refs
    folder = vault / "media"
    folder.mkdir(exist_ok=True)
    with ExitStack() as cleanup:
        copies = []
        for file in files:
            digest = hashlib.sha256()
            with file.open("rb") as source, tempfile.NamedTemporaryFile(dir=folder, delete=False) as tmp:
                staged = Path(tmp.name)
                cleanup.callback(staged.unlink, missing_ok=True)
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
                    tmp.write(block)
            dest = folder / (digest.hexdigest() + file.suffix.lower())
            refs.append({"name": file.name, "path": dest.relative_to(vault).as_posix()})
            copies.append((staged, dest))
        with ExitStack() as unpublished:
            for staged, dest in copies:
                if not dest.exists():
                    os.replace(staged, dest)
                    unpublished.callback(dest.unlink, missing_ok=True)
            unpublished.pop_all()
    return refs


def source_lines(text):
    """Separate the reserved source section so originals never appear in a shared book."""
    ordinary, sources = [], []
    inside = False
    for line in text.splitlines():
        if line.startswith(("# ", "## ")):
            inside = line.strip() in SOURCE_HEADINGS
            if inside:
                continue
        (sources if inside else ordinary).append(line)
    return ordinary, sources


def linked_media(text):
    _, lines = source_lines(text)
    links = [MEDIA_LINK.fullmatch(line.strip()) for line in lines]
    return [{"name": m[1], "path": m[2], **({"step": int(m[3])} if m[3] else {}),
             **({"at": m[4]} if m[4] else {})} for m in links if m]


def add_sources(text, refs, lang, transcript_link=None, step=None, at=None):
    if not refs and not transcript_link:
        return text
    before, sources = source_lines(text)
    present = {(m["path"], m.get("step"), m.get("at")) for m in linked_media(text)}
    additions = []
    if transcript_link and transcript_link not in sources:
        additions.append(transcript_link)
    for ref in refs:
        key = (ref["path"], step, at)
        if key in present:
            continue
        present.add(key)
        label = ref["name"].replace("[", "［").replace("]", "］")
        label = " ".join(label.splitlines())
        locator = (f" · 步骤 {step}" if lang == "zh" else f" · Step {step}") if step else ""
        if at:
            locator += f" · {at}"
        additions.append(f"- [{label}](../{ref['path']}){locator}")
    if not additions:
        return text
    heading = "## 原始素材" if lang == "zh" else "## Original sources"
    return "\n".join(before).rstrip() + "\n\n" + heading + "\n\n" + "\n".join(sources + additions).strip() + "\n"


def interview_dir(vault, key):
    if not re.fullmatch(r"[a-f0-9]{24}", str(key)):
        raise ValueError(f"invalid interview id: {key}")
    return vault / "interviews" / key


def read_interview(vault, key):
    path = interview_dir(vault, key) / "session.json"
    if not path.is_file():
        raise ValueError(f"interview not found: {key}")
    return json.loads(path.read_text(encoding="utf-8"))


def segment_ranges(lines, starts):
    nonempty = [i for i, line in enumerate(lines, 1) if line.strip()]
    if not nonempty:
        raise ValueError("the transcript is empty")
    if starts is None:
        starts = [i for i in nonempty if i == 1 or not lines[i-2].strip()]
    if starts != sorted(set(starts)) or starts[0] != nonempty[0] or not set(starts) <= set(nonempty):
        raise ValueError("segment starts must be ascending nonblank line numbers, including the first nonblank line")
    ends = starts[1:] + [len(lines) + 1]
    ranges = []
    for first, stop in zip(starts, ends):
        last = stop - 1
        while not lines[last-1].strip():
            last -= 1
        ranges.append([first, last])
    return ranges


def start_interview(vault, transcript, starts, title, files):
    path = Path(transcript).expanduser()
    raw = path.read_bytes()
    lines = raw.decode("utf-8-sig").splitlines()
    # Equivalent Windows and Unix transcripts share progress, while the first original stays byte-exact.
    key = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:24]
    folder = interview_dir(vault, key)
    ranges = segment_ranges(lines, starts)
    if (folder / "session.json").exists():
        session = read_interview(vault, key)
        if starts and ranges != session["ranges"]:
            raise ValueError("this transcript already has a saved segment plan")
    else:
        session = {"id": key, "title": title or path.stem, "name": path.name, "ranges": ranges, "media": []}
    refs = archive_media(vault, files)
    known = {ref["path"] for ref in session["media"]}
    for ref in refs:
        if ref["path"] not in known:
            session["media"].append(ref)
            known.add(ref["path"])
    folder.mkdir(parents=True, exist_ok=True)
    original = folder / "transcript.txt"
    if not original.exists():
        atomic_bytes(original, raw)
    atomic_bytes(folder / "session.json", (json.dumps(session, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return session


def get_range(session, number):
    if not 1 <= number <= len(session["ranges"]):
        raise ValueError(f"unknown segment number: {number}")
    return session["ranges"][number-1]
