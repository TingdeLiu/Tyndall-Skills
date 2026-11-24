# 独家记忆

**让 AI 成为更懂你的聊天朋友。**

把你愿意留下的经历记下来。换个新对话，聊到同一件事，它还能接着上次的话聊。你也可以决定这位朋友有什么性格。

> 「以后你叫阿栗吧。跟我说话直一点，你不同意我的时候也告诉我。」

## 开始用

在 Codex 里直接发这句：

```text
请安装「独家记忆」：https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

也可以在项目目录运行下面的命令，选择 Codex 或 Claude Code。安装器使用 Node.js，归档和检索脚本使用 Python 3 标准库。[安装器说明](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

安装后就能聊。第一次想留下经历或长期设定朋友性格时，选一个自己的文件夹。此后在能访问它的新对话里使用「独家记忆」，就能接着聊。你的经历存为 Markdown，可附照片、录音和视频。朋友的性格写在 `SOUL.md`，你随时可以改。聊天中用到的内容会经过你使用的 AI 服务。[English](README.md)

## 有些故事，你也许想留给家人

哪怕只是想让将来的自己重新听一段声音，也可以把原始录音和故事放在一起。如果希望自己离世后，家人还能听你讲往事，可以提前挑好愿意留下的故事，做成可打印的回忆录，或者带原声的离线记忆卡，把成品交给信任的人保管。交给谁、什么时候交，由你安排。

《外公的敲门声》是一张虚构的示例卡。下载并解压 ZIP，打开 `index.html`，可以问「外公怎么敲门」，再听那三声。家人也可以把这份 ZIP 给装了技能的 Codex，只围绕你选好的故事提问。卡里包含选中素材的完整原件，声音来自你留下的录音。[听 3 秒示例](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [下载示例卡](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip) · [预览](examples/knock-zh.png)
