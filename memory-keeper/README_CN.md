# 独家记忆

把只属于你的经历留下来。以后和 AI 聊天，你可以从今天最想说的那句开始。它能翻回你愿意记下的往事，接着聊。每段记忆都是你自己文件夹里的 Markdown，照片、录音和视频也可以一起留。安装名为 `memory-keeper`。[English](README.md)

## 两次聊天，中间可以隔很久

下面是一个虚构的例子。

**第一次，你想记一件小事。**「帮我记一下。第一次一个人搬家，头几天连饭都吃得很随便。后来找到楼下卖豆浆的小店，每天早上有个地方去，才慢慢觉得自己住下来了。」AI 给你看整理好的文字，确认后存到你的记忆库。

**过了几个月，你又想聊聊。**「下个月要搬家了，心里有点乱。」如果当初那段经历跟今天有关，AI 可以接一句：「你上次说，找到楼下那家豆浆店，才觉得自己住下来了。这回让你心里乱的是什么？」

你也可以说「这次我挺期待的，今天就想跟你说说」。它会跟着你今天的感受聊。闲聊本身不会自动变成一篇记录。你想核对它记得对不对，可以问「我当时怎么说的？」，打开原文看。

## 开始用

在 Codex 里直接发这句：

```text
请安装「独家记忆」：https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

也可以在项目目录运行下面的命令，选择 Codex 或 Claude Code。安装器使用 Node.js，归档和检索脚本使用 Python 3 标准库。[安装器说明](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

想先试聊，可以说「陪我聊聊最近的事」。第一次说「这段我想留下来」时，再选一个存放记忆的文件夹。以后，只要用的 AI 有权读取这个库，就可以接着聊。换聊天工具时，也可以只给它看你选的一篇 Markdown。聊天中用到的内容会经过你使用的 AI 服务。

## 有些故事，你也许想留给家人

哪怕只是想让将来的自己重新听一段声音，也可以把原始录音和故事放在一起。如果希望自己离世后，家人还能听你讲往事，可以提前挑好愿意留下的故事，做成可打印的回忆录，或者带原声的离线记忆卡，把成品交给信任的人保管。交给谁、什么时候交，由你安排。

《外公的敲门声》是一张虚构的示例卡。下载并解压 ZIP，打开 `index.html`，可以问「外公怎么敲门」，再听那三声。家人也可以把这份 ZIP 给装了技能的 Codex，只围绕你选好的故事提问。卡里包含选中素材的完整原件，声音来自你留下的录音。[听 3 秒示例](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [下载示例卡](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip) · [预览](examples/knock-zh.png)
