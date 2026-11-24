# memory-keeper

**照常聊天，让 AI 越来越懂你。**

开启聊天记忆后，你说起的经历、在意的事、喜欢的相处方式，AI 会在聊天时留意，慢慢拼出一份关于你的画像。它也有自己的性格。你可以叫它直说，它也能从你的反馈里学会，什么时候说看法，什么时候先听你讲。

> 你上次随口说，面试前跟朋友练过开头，心里就稳多了。下回再聊起面试，它可以直接问：「要不要我当面试官，陪你开个头？」

## 开始用

在 Codex 里直接发这句：

```text
请安装 memory-keeper 这个 Skill：https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

也可以在项目目录运行下面的命令，选择 Codex 或 Claude Code。安装器使用 Node.js，归档和检索脚本使用 Python 3 标准库。[安装器说明](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

第一次选一个本地文件夹，告诉它是否开启聊天记忆。此后在能读这个文件夹的对话里使用本技能，直接聊就好。随时可以说「这段别记」「先关掉自动记忆」「你为什么觉得我喜欢这样？」。用到的聊天内容会经过你选择的 AI 服务。[English](README.md)

## 它是怎么慢慢认识你的

| 打开什么 | 里面有什么 |
|---|---|
| `profile.md` | 你的个人画像。比如「准备面试时，先练开头会安心一些」。 |
| `SOUL.md` | AI 的名字、性格，以及它从相处中形成的习惯。比如「我说话直，遇到他为面试发愁，我会先陪他练一句」。 |
| `memories/` | 形成这些印象的具体经历和原话，也可以附照片、录音和视频。 |

两份档案里自动整理出的每一条都有来源。你可以纠正一条印象、改它的性格，也可以只聊天、暂停积累。

<details>
<summary>把选好的故事留给亲友</summary>

哪怕只是想让将来的自己重新听一段声音，也可以把原始录音和故事放在一起。如果希望自己离世后，家人还能听你讲往事，可以提前挑好愿意留下的故事，做成可打印的回忆录，或者带原声的离线记忆卡，把成品交给信任的人保管。交给谁、什么时候交，由你安排。

《外公的敲门声》是一张虚构的示例卡。下载并解压 ZIP，打开 `index.html`，可以问「外公怎么敲门」，再听那三声。家人也可以把这份 ZIP 给装了技能的 Codex，只围绕你选好的故事提问。卡里包含选中素材的完整原件，声音来自你留下的录音。[听 3 秒示例](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [下载示例卡](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip) · [预览](examples/knock-zh.png)

</details>
