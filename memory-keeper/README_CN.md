# Memory Keeper · 家庭记忆

[English](README.md) · [听 3 秒敲门声](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [下载整张示例卡](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip)

**你还记得外公怎么敲门吗？** 把那两轻一重的敲门声，和你认出他的那句话放在一起，做成一张家人能点开听的记忆卡。你可以在 Codex 或 Claude Code 里跟它聊，故事和原件都存在自己选的文件夹里。

[![《外公的敲门声》记忆卡截图，正文下方可以播放敲门声](examples/knock-zh.png)](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-zh.zip)

**先听一张，再决定要不要装。** 下载上面的示例，解压整个 ZIP，用浏览器打开 `index.html`，按播放键听那两轻一重。故事是虚构的，敲门声为合成示例。以后家人收到你的卡，也这样打开，断网照样能听。

## 做自己的第一张卡

用 Codex 的话，可以直接在对话里发这句：

```text
请安装这个家庭记忆技能：https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Codex 和 Claude Code 也可以在项目目录运行下面的命令，再选择自己用的工具。安装器用 Node.js。做记忆卡、保存原件和导出成书用 Python 3 标准库。[安装器要求](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

1. **先留一句话。**「帮我记一下，外公来我家，轻轻敲两下，等一等，再重重敲一下。我在屋里就知道是他。」第一次它会推荐一个文件夹，把整理好的文字给你过目。
2. **配上一件原件。** 给它一段本地录音或一张照片，说「把这个和刚才的故事放在一起」。记录一道家常菜或一门手艺时，还可以告诉它哪张照片、视频里的哪几秒对应哪一步。
3. **做给一个人。**「把这个故事和刚才那段录音做张卡，我想给姐姐听。」成品在记忆库的 `exports/` 文件夹里，你自己决定发给谁。

## 下次回家时，还能这样用

- **出发前**说「我想问问我妈第一次上班的事，帮我想个开头，一次问一个问题」。
- **回家后**说「接着整理上次那份采访」。保存过的转写会记住进度，每段整理好的故事都能找到原文行号。
- **过生日前**说「把外婆讲过的故事做成一本书」。浏览器打开就可以打印，也能另存成 PDF。

每篇故事都是能直接打开和编辑的 Markdown 文件。备份时复制整个记忆库，照片和声音就能跟着搬家。聊天内容会经过你使用的 AI 服务。记忆卡带上你点名的**完整原件**，包括时间标记之外的录音，以及照片里原有的拍摄信息。分享标为私密的故事需要明确确认。

打算下次回家再试，可以先在仓库右上角点 **Star**，到时候从收藏里找回来。如果试用时卡在哪一步，欢迎用虚构例子来提建议。[收藏仓库](https://github.com/TingdeLiu/Tyndall-Skills) · [反馈使用体验](https://github.com/TingdeLiu/Tyndall-Skills/issues)
