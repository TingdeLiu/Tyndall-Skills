import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "scripts" / "memory_vault.py"
STORY = """---
type: memory
title: 包粽子
summary: 外婆教我包粽子。
narrator: 我
people: [外婆]
event_date: 1998 年夏天
---
## 做法

1. 把叶子折成漏斗。
2. 把米填进去。
"""


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="memory-keeper-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.vault = self.root / "记忆库"
        self.env = dict(os.environ, MEMORY_KEEPER_CONFIG=str(self.root / "config.json"))
        self.cli("init", self.vault)

    def run_cli(self, *args, draft=None):
        return subprocess.run([sys.executable, "-B", "-X", "utf8", str(CLI), *map(str, args)],
                              input=draft, encoding="utf-8", capture_output=True, env=self.env)

    def cli(self, *args, draft=None):
        result = self.run_cli(*args, draft=draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def fixture(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_new_chat_loads_the_selected_companion_and_owner(self):
        soul = self.vault / "SOUL.md"
        self.assertIn("坦率", soul.read_text(encoding="utf-8"))
        soul.write_text("# 阿栗\n说话直一点。\n", encoding="utf-8")
        (self.vault / "profile.md").write_text("# 我叫小棠\n", encoding="utf-8")
        self.cli("init", self.vault)
        second = self.root / "another vault"
        self.cli("init", second, "--language", "en")
        self.assertIn("candid", self.cli("chat-context")["companion"])
        self.assertEqual(self.cli("chat-context", "--vault", self.vault), {
            "vault": self.vault.resolve().as_posix(),
            "chat_memory": "unset",
            "companion": "# 阿栗\n说话直一点。\n",
            "owner_profile": "# 我叫小棠\n",
            "memories": [],
        })
        old_soul = second / "SOUL.md"
        old_soul.unlink()
        self.assertIn("candid", self.cli("chat-context")["companion"])
        self.assertFalse(old_soul.exists())

    def test_everyday_chat_grows_two_sourced_documents_and_pause_is_per_vault(self):
        def draft(words, profile, habit):
            return (f"---\ntype: memory\ntitle: 面试开场\nsummary: 面试前的习惯\nnarrator: 我\n"
                    f"chat_topic: 面试准备\nprofile_note: {profile}\ncompanion_note: {habit}\n---\n"
                    f"## 原话\n\n> {words}\n")
        first = draft("我面试前喜欢练第一句。你刚才陪我试了那遍就挺好。", "面试前练开场会安心。", "先陪他练一句。")
        self.cli("init", self.vault, "--auto-save")
        self.assertNotEqual(self.run_cli("add", "-", "--from-chat", draft=first).returncode, 0)
        soul = self.vault / "SOUL.md"
        soul.write_text("# 阿栗\n我很坦率，也可以不同意你。\n", encoding="utf-8")
        self.cli("chat-memory", "on")
        for invalid in [first.replace("narrator: 我", "narrator: 妈妈"),
                        first.replace("narrator: 我", "narrator: 我\ntags: [私密]"),
                        first.replace("## 原话", "## 摘要")]:
            self.assertNotEqual(self.run_cli("add", "-", "--from-chat", draft=invalid).returncode, 0)
        with ThreadPoolExecutor(2) as pool:
            attempts = list(pool.map(lambda _: self.cli("add", "-", "--from-chat", draft=first), range(2)))
        self.assertEqual(len({a["id"] for a in attempts}), 1)
        self.assertTrue(any(a.get("already_saved") for a in attempts))
        old_id = attempts[0]["id"]
        self.assertIn(old_id, soul.read_text(encoding="utf-8"))
        again = self.cli("chat-context")
        self.assertIn("练开场会安心", again["owner_profile"])
        self.assertNotIn("先陪他练一句", again["owner_profile"])
        self.assertIn("先陪他练一句", again["companion"])
        self.assertIn("我很坦率", again["companion"])
        second = draft("现在面试我更喜欢自己准备。留点时间给我。", "现在喜欢自己准备。", "给他留出准备时间。")
        new = self.cli("add", "-", "--from-chat", draft=second)
        self.assertNotIn("练开场会安心", self.cli("chat-context")["owner_profile"])
        self.assertIn("自己准备", (self.vault / "profile.md").read_text(encoding="utf-8"))
        self.cli("chat-memory", "off")
        self.assertNotEqual(self.run_cli("add", "-", "--from-chat", draft=second).returncode, 0)
        self.assertIn("给他留出准备时间", self.cli("chat-context")["companion"])
        newpath = self.vault / new["written"]
        newpath.write_text(newpath.read_text(encoding="utf-8").replace("type: memory", "type: memory\ntags: [private]"), encoding="utf-8")
        self.assertNotIn("给他留出准备时间", self.cli("chat-context")["companion"])
        self.cli("chat-memory", "on")
        self.assertEqual(self.cli("add", "-", "--from-chat", draft=second), {"already_saved": True, "dry_run": False})
        self.cli("chat-memory", "off")
        self.cli("remove", old_id)
        self.assertNotIn("给他留出准备时间", soul.read_text(encoding="utf-8"))
        self.assertNotIn("先陪他练一句", soul.read_text(encoding="utf-8"))
        self.cli("init", self.root / "other", "--language", "en")
        self.assertEqual(self.cli("chat-memory")["chat_memory"], "unset")
        self.assertEqual(self.cli("chat-memory", "--vault", self.vault)["chat_memory"], "off")

    def test_personal_chat_finds_own_recollections_across_sessions(self):
        def save(title, narrator, tags=""):
            draft = STORY.replace("包粽子", title).replace("narrator: 我", f"narrator: {narrator}")
            return self.cli("add", "-", draft=draft.replace("people: [外婆]", f"people: [我]\ntags: [{tags}]"))["id"]

        my_story = save("搬家后学做饭", "我")
        english = save("第二次搬家", "me")
        interview = save("妈妈记得我搬家", "妈妈")
        private = save("搬家的另一个原因", "我", "private")
        legacy = self.vault / "memories" / "搬家旧笔记.md"
        legacy.write_text(STORY.replace("narrator: 我\n", ""), encoding="utf-8")
        everyday = self.cli("search", "搬家", "--mine", "--no-private")["results"]
        self.assertEqual({r["id"] for r in everyday}, {my_story, english})
        self.assertTrue(all((self.vault / r["path"]).is_file() for r in everyday))
        self.assertEqual({r["id"] for r in self.cli("search", "搬家", "--mine")["results"]},
                         {my_story, english, private})
        self.assertIn(interview, {r["id"] for r in self.cli("search", "搬家", "--person", "我")["results"]})
        self.assertEqual(self.cli("search", "--type", "person", "--mine")["count"], 0)

    def test_chat_recall_uses_saved_interview_words_and_respects_later_edits(self):
        quote = "上次面试前，朋友陪我练了第一句。开了口就好了。"
        transcript = self.root / "采访.txt"
        transcript.write_text("哪次面试感觉好一点？\n" + quote, encoding="utf-8")
        session = self.cli("interview", "start", transcript)
        def draft(title, summary, body, narrator="我", tags="聊天", date="2026-02-01"):
            return (f"---\ntype: memory\ntitle: {title}\nsummary: {summary}\nnarrator: {narrator}\n"
                    f"tags: [{tags}]\nrecorded: {date}\n---\n\n## 原话\n\n> {body}\n")

        saved = self.cli("add", "-", "--interview", session["id"], "--segment", 1,
                         draft=draft("面试的第一句", "朋友陪我练过开场。", quote, tags="本人采访"))
        for n in range(3):
            self.cli("add", "-", draft=draft(f"路过面试地点{n}", "下车买水。", "随便走了走。", date="2026-03-01"))
        self.cli("add", "-", draft=draft("私下那场面试", "开场", "私密原话", tags="私密"))
        self.cli("add", "-", draft=draft("别人的面试", "开场", "妈妈的经历", narrator="妈妈"))

        results = self.cli("chat-context", "面试", "开场", "紧张")["memories"]
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["path"], saved["written"])
        self.assertIn(quote, results[0]["excerpt"])
        self.assertNotIn("transcript.txt", results[0]["excerpt"])
        self.assertTrue(all("路过" in result["title"] for result in results[1:]))
        self.assertEqual(self.cli("search", "--mine", "--tag", "本人采访")["results"][0]["id"], saved["id"])
        self.assertEqual(self.cli("chat-context", "滑雪")["memories"], [])
        self.assertEqual(self.cli("chat-context", session["id"])["memories"], [])
        path = self.vault / saved["written"]
        path.write_text(path.read_text(encoding="utf-8").replace(quote, "这次我想自己练开场。"), encoding="utf-8")
        self.assertIn("自己练开场", self.cli("chat-context", "开场")["memories"][0]["excerpt"])
        self.cli("remove", saved["id"])
        self.assertEqual(self.cli("chat-context", "开场")["memories"], [])

    def test_attach_originals_to_new_and_old_memory(self):
        files = [self.fixture("原声.m4a", b"voice"), self.fixture("折叶[1].heic", b"photo"),
                 self.fixture("手法.MOV", b"video" * 300000)]
        self.cli("add", "-", "--attach", files[0], "--dry-run", draft=STORY)
        self.assertFalse((self.vault / "media").exists())
        saved = self.cli("add", "-", "--attach", files[0], draft=STORY)
        for step, clip in [(1, "00:02"), (2, "00:11–00:19"), (2, "00:11–00:19")]:
            self.cli("media", saved["id"], files[2], "--step", step, "--at", clip)
        stored_movie = next(m["path"] for m in self.cli("media", saved["id"])["media"] if m.get("step") == 1)
        self.cli("media", saved["id"], "--reuse", stored_movie, "--step", 2, "--at", "00:11–00:19")
        refs = self.cli("media", saved["id"], files[1], "--step", 1)["media"]
        self.assertEqual(len(refs), 4)
        self.assertEqual(len(list((self.vault / "media").iterdir())), 3)
        relocated = self.root / "搬家后"
        shutil.copytree(self.vault, relocated)
        self.assertEqual(self.cli("media", saved["id"], "--vault", relocated)["media"], refs)
        self.assertEqual({(relocated / m["path"]).read_bytes() for m in refs}, {f.read_bytes() for f in files})
        for ref in refs:
            self.assertIn("../" + ref["path"], (relocated / saved["written"]).read_text(encoding="utf-8"))
        self.assertTrue(self.cli("check", relocated)["ok"])
        (relocated / refs[0]["path"]).unlink()
        self.assertFalse(self.cli("check", relocated, "--fix")["ok"])
        self.cli("remove", saved["id"])
        self.assertTrue(all((self.vault / m["path"]).exists() for m in refs))

    def test_bad_media_does_not_publish_partial_memory(self):
        photo = self.fixture("照片.png", b"png")
        result = self.run_cli("add", "-", "--attach", photo, "--attach", self.root / "absent.mp4", draft=STORY)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list((self.vault / "memories").iterdir()))
        self.assertFalse((self.vault / "media").exists())

    def test_card_shares_one_story_and_only_chosen_originals(self):
        clip = self.fixture("做法.mov", b"chosen original bytes")
        other = self.fixture("私下的聊天.m4a", b"excluded")
        transcript = self.fixture("长采访.txt", b"other family details")
        session = self.cli("interview", "start", transcript)
        story = self.cli("add", "-", "--interview", session["id"], "--segment", 1,
                         draft=STORY.replace("包粽子", "包粽子 & <米>"))["id"]
        selection = self.cli("media", story, clip, "--step", 2, "--at", "01:02.5–01:05")["media"][0]["path"]
        self.cli("media", story, "--reuse", selection, "--step", 3, "--at", "01:05")
        self.cli("interview", "start", transcript, "--attach", other)
        hidden = self.cli("media", story)["interview_media"][0]["path"]
        self.assertNotEqual(self.run_cli("card", story, "--media", hidden).returncode, 0)
        self.assertNotEqual(self.run_cli("card", story, "--media", "../profile.md").returncode, 0)
        (self.vault / "SOUL.md").write_text("私人聊天设定", encoding="utf-8")
        with zipfile.ZipFile(self.cli("card", story)["written"]) as archive:
            self.assertEqual(archive.namelist(), ["index.html", "stories.json"])
            self.assertNotIn("做法.mov", archive.read("index.html").decode())
            for name in archive.namelist():
                self.assertNotIn("私人聊天设定", archive.read(name).decode())
        card = self.cli("card", story, "--media", selection, "--media", selection)
        with zipfile.ZipFile(card["written"]) as archive:
            self.assertEqual(archive.namelist(), ["index.html", "stories.json", "media/1.mov"])
            self.assertEqual(archive.read("media/1.mov"), clip.read_bytes())
            page = archive.read("index.html").decode()
            self.assertIn("包粽子 &amp; &lt;米&gt;", page)
            self.assertIn('src="media/1.mov#t=62.5,65"', page)
            self.assertIn('src="media/1.mov#t=65"', page)
            for text in [selection, session["id"], "原始转写", "私下的聊天", str(self.vault)]:
                self.assertNotIn(text, page)
        (self.vault / selection).unlink()
        snapshot = set((self.vault / "exports").iterdir())
        self.assertNotEqual(self.run_cli("card", story, "--media", selection).returncode, 0)
        self.assertEqual(snapshot, set((self.vault / "exports").iterdir()))

    def test_private_card_requires_explicit_permission_and_keeps_versions(self):
        private = STORY.replace("type: memory", "type: memory\ntags: [private]")
        story = self.cli("add", "-", draft=private)["id"]
        self.assertNotEqual(self.run_cli("card", story).returncode, 0)
        first = self.cli("card", story, "--include-private")
        second = self.cli("card", story, "--include-private")
        self.assertNotEqual(first["written"], second["written"])
        self.assertIn("私密版", first["written"])
        with zipfile.ZipFile(first["written"]) as archive:
            self.assertIn("私密版", archive.read("index.html").decode())

    def test_family_can_question_two_stories_without_access_to_a_vault(self):
        voice = self.fixture("妈妈的声音.wav", b"family original")
        first = self.cli("add", "-", "--attach", voice, draft=STORY)["id"]
        second = self.cli("add", "-", draft=STORY.replace("包粽子", "车站")
                          .replace("我\npeople", "妈妈\npeople") + "\n> 她送我到车站。\n")["id"]
        private = self.cli("add", "-", draft=STORY.replace("包粽子", "未分享的信")
                           .replace("type: memory", "type: memory\ntags: [private]"))["id"]
        self.assertNotEqual(self.run_cli("card", first, private).returncode, 0)
        original = self.cli("media", first)["media"][0]["path"]
        package = self.cli("card", second, first, second, "--media", original)
        self.assertEqual(package["stories"], 2)
        # A recipient may even have a broken private configuration. The shared reader
        # must never consult it, including on a follow-up or an unknown story id.
        Path(self.env["MEMORY_KEEPER_CONFIG"]).write_text("not valid JSON", encoding="utf-8")
        path = Path(package["written"])
        with zipfile.ZipFile(path) as bundle:
            page = bundle.read("index.html").decode()
            data = bundle.read("stories.json").decode()
            bundle.extractall(self.root / "received")
        for unseen in (private, "未分享的信", original, str(self.vault)):
            self.assertNotIn(unseen, data + page)
        listing = self.cli("read-share", path)["stories"]
        self.assertEqual([s["title"] for s in listing], ["车站", "包粽子"])
        self.assertIn("妈妈", listing[0]["context"])
        station = self.cli("read-share", self.root / "received", "--story", "s1")
        quoted = next(p for p in station["passages"] if p["kind"] == "quotation")
        self.assertEqual(quoted["text"], "她送我到车站。")
        self.assertIn(f'id="{quoted["anchor"]}"', page)
        self.assertEqual(station["media"], [])
        kitchen = self.cli("read-share", path, "--story", "s2")
        media = kitchen["media"][0]
        self.assertEqual((self.root / "received" / media["file"]).read_bytes(), voice.read_bytes())
        self.assertIn(f'id="{media["anchor"]}"', page)
        self.assertNotEqual(self.run_cli("read-share", path, "--story", "s3").returncode, 0)

    def test_recipient_can_recognize_an_old_card_without_a_vault(self):
        old = self.root / "old.zip"
        with zipfile.ZipFile(old, "w") as bundle:
            bundle.writestr("index.html", "<p>Family story</p>")
        Path(self.env["MEMORY_KEEPER_CONFIG"]).unlink()
        result = self.run_cli("read-share", old)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("index.html", result.stderr)
        self.assertFalse(Path(self.env["MEMORY_KEEPER_CONFIG"]).exists())

    def test_interview_progress_and_concurrent_retry(self):
        text = "\ufeff外婆说，先折叶。\r\n要折出一个角。\r\n\r\n然后填米。\r\n"
        transcript = self.fixture("采访.txt", text.encode())
        recording = self.fixture("原声.wav", b"original")
        session = self.cli("interview", "start", transcript, "--starts", 1, 4, "--attach", recording)
        key = session["id"]
        self.assertEqual([s["lines"] for s in session["segments"]], [[1, 2], [4, 4]])
        self.assertEqual((self.vault / session["transcript"]).read_bytes(), text.encode())
        self.assertEqual(self.cli("interview", "show", key, "--segment", 2)["text"], "然后填米。")
        add = ("add", "-", "--interview", key, "--segment", 1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, retry = pool.map(lambda _: self.cli(*add, draft=STORY), range(2))
        self.assertEqual(first["id"], retry["id"])
        self.assertEqual(len(list((self.vault / "memories").iterdir())), 1)
        resumed = self.cli("interview", "start", transcript)
        self.assertEqual([s["status"] for s in resumed["segments"]], ["confirmed", "pending"])
        unix_copy = self.fixture("copy.txt", text.lstrip("\ufeff").replace("\r\n", "\n").encode())
        self.assertEqual(self.cli("interview", "start", unix_copy)["id"], key)
        self.assertEqual((self.vault / session["transcript"]).read_bytes(), text.encode())
        self.assertEqual(len(self.cli("media", first["id"])["interview_media"]), 1)
        self.assertEqual(self.cli("interview", "list")["interviews"][0]["pending"], 1)
        (self.vault / "people/外婆.md").unlink()
        (self.vault / "INDEX.md").unlink()
        self.assertTrue(self.cli(*add, draft=STORY)["already_saved"])
        self.assertTrue(self.cli("check")["ok"])
        mismatch = self.run_cli("interview", "start", transcript, "--starts", 1, 2)
        self.assertNotEqual(mismatch.returncode, 0)
        self.cli("add", "-", "--interview", key, "--segment", 2, draft=STORY)
        self.assertEqual(self.cli("interview", "list")["interviews"][0]["pending"], 0)
        self.cli("remove", first["id"])
        self.assertEqual(self.cli("interview", "list")["interviews"][0]["pending"], 1)

    def test_shared_editions_exclude_originals(self):
        photo = self.fixture("私人原片（待确认）.jpg", b"photo")
        self.cli("add", "-", "--attach", photo, draft=STORY)
        secret = STORY.replace("title: 包粽子", "title: 星期六\ntags: [私密]").replace("把米填进去", "商量搬家")
        self.cli("add", "-", draft=secret)
        family = Path(self.cli("export")["written"])
        family_text = family.read_text(encoding="utf-8")
        personal = Path(self.cli("export", "--include-private")["written"])
        self.assertNotEqual(personal, family)
        self.assertEqual(family.read_text(encoding="utf-8"), family_text)
        self.assertIn("<ol><li>把叶子折成漏斗。", family_text)
        self.assertNotIn("商量搬家", family_text)
        private_text = personal.read_text(encoding="utf-8")
        self.assertIn("私密版", private_text)
        self.assertIn("商量搬家", private_text)
        for book in (family_text, private_text):
            self.assertNotIn("私人原片", book)
            self.assertNotIn("../media/", book)
        self.assertNotEqual(Path(self.cli("export")["written"]), family)
        self.assertNotEqual(self.run_cli("export", "--include-private", "--out", family).returncode, 0)
        private_item = next(m for m in self.cli("timeline")["items"] if m["private"])
        self.assertEqual((private_item["year"], private_item["summary"]), (None, ""))

    def test_alias_and_correction_preserve_authored_notes(self):
        memory = self.cli("add", "-", draft=STORY)
        self.cli("alias", "外婆", "姥姥")
        self.assertEqual(self.cli("search", "--type", "memory", "--person", "姥姥")["count"], 1)
        extra = self.cli("add", "-", draft=STORY.replace("外婆", "姥姥"))
        self.assertFalse((self.vault / "people/姥姥.md").exists())
        self.assertEqual(self.cli("export", "--person", "姥姥")["memories"], 2)
        self.assertEqual(self.cli("timeline", "--person", "姥姥")["count"], 2)
        old_person = self.vault / "people/外婆.md"
        old_person.write_text(old_person.read_text(encoding="utf-8") + "\n## 随手补充\n\n- 她爱吃甜粽。\n", encoding="utf-8")
        story = self.vault / memory["written"]
        story.write_text(story.read_text(encoding="utf-8").replace("people: [外婆]", "people: [奶奶]"), encoding="utf-8")
        self.assertFalse(self.cli("check")["ok"])
        self.assertTrue(self.cli("check", "--fix")["ok"])
        self.assertTrue(self.cli("check")["ok"])
        old_text = old_person.read_text(encoding="utf-8")
        self.assertNotIn(f"[[{memory['id']}]]", old_text)
        self.assertIn(f"[[{extra['id']}]]", old_text)
        self.assertIn("她爱吃甜粽", old_text)
        self.assertIn("- 人物：[[奶奶]]", story.read_text(encoding="utf-8"))
        self.assertEqual(self.cli("search", "--type", "memory", "--person", "姥姥")["count"], 1)
        self.assertNotEqual(self.run_cli("alias", "奶奶", "姥姥").returncode, 0)

    def test_legacy_private_alias_and_english_vault(self):
        self.cli("init", self.vault, "--language", "en")
        self.cli("add", "-", draft=STORY.replace("外婆", "Grandma"))
        private = STORY.replace("外婆", "Nana").replace("title: 包粽子", "title: Saturday\ntags: [private]")
        self.cli("add", "-", draft=private)
        self.cli("alias", "Grandma", "Nana")
        self.assertEqual(self.cli("search", "--type", "memory", "--person", "Grandma")["count"], 2)
        self.assertEqual(self.cli("export", "--person", "Nana")["memories"], 1)
        book = self.cli("export", "--person", "Nana", "--include-private")
        self.assertEqual(book["memories"], 2)
        self.assertIn("Private edition", Path(book["written"]).read_text(encoding="utf-8"))
        self.assertTrue(self.cli("check")["ok"])


if __name__ == "__main__":
    unittest.main()
