# memory-keeper

**留下自己的独家记忆，让 AI 越聊越懂你。**

从聊天里挑一句你希望它记得的话，也可以请它采访你。下次换个对话，它能找回你当时的原话，接着聊。

> 「你采访我吧，一次问一件事。聊完让我挑，哪些话留给下次。」

## 开始用

在 Codex 里直接发这句：

```text
请安装 memory-keeper 这个 Skill：https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

也可以在项目目录运行下面的命令，选择 Codex 或 Claude Code。安装器使用 Node.js，归档和检索脚本使用 Python 3 标准库。[安装器说明](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

安装后就能聊。第一次想留下经历或长期设定朋友性格时，选一个自己的文件夹。此后在能访问它的新对话里使用 memory-keeper，就能接着聊。你的经历存为 Markdown，可附照片、录音和视频。朋友的性格写在 `SOUL.md`，你随时可以改。聊天中用到的内容会经过你使用的 AI 服务。[English](README.md)

## 拿一段旧聊天试试

把一段和 AI 的聊天贴进来，说「帮我挑出下次还想接着聊的事」。它会分清哪些话是你说的，把原话给你看，由你挑选。下次如果问「我上次是怎么说的」，它还能给你那段记录的位置。哪句记偏了，可以直接改。

<details>
<summary>把选好的故事留给亲友</summary>

哪怕只是想让将来的自己重新听一段声音，也可以把原始录音和故事放在一起。如果希望自己离世后，家人还能听你讲往事，可以提前挑好愿意留下的故事，做成可打印的回忆录，或者带原声的离线记忆卡，把成品交给信任的人保管。交给谁、什么时候交，由你安排。

《外公的敲门声》是一张虚构的示例卡。下载并解压 ZIP，打开 `index.html`，可以问「外公怎么敲门」，再听那三声。家人也可以把这份 ZIP 给装了技能的 Codex，只围绕你选好的故事提问。卡里包含选中素材的完整原件，声音来自你留下的录音。[听 3 秒示例](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [下载示例卡](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip) · [预览](examples/knock-zh.png)

</details>
