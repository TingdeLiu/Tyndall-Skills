# 独家记忆 · Your personal memory journal

Keep the moments you want to remember. The next time you talk to your AI, you can start with what’s on your mind today. It can draw on experiences you chose to save. Your stories are Markdown files in a folder you control, alongside any photos, recordings or video you keep with them. The skill installs as `memory-keeper`. [中文](README_CN.md)

## Two conversations, months apart

Here’s a fictional example.

**When you want to remember something.** “Save this for me. When I first moved out on my own, I hardly bothered with meals. Then I found a little place downstairs that sold soy milk. Having somewhere to go for breakfast made it feel like I lived there.” The AI shows you a draft and saves it to your journal when you confirm.

**When you just want to talk.** Months later, you say, “I’m moving again next month. My head’s all over the place.” Your AI can pick up that thread. “You once told me finding that little breakfast place helped you feel settled. What’s on your mind about this move?”

You can say, “Actually, I’m looking forward to this one. I just felt like talking.” Today’s conversation follows how you feel now. An ordinary chat doesn't create a journal entry. Ask “What did I actually say?” to see the original passage.

## Get started

In Codex, paste this request.

```text
Install my personal memory journal from https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Or run this in your project and select Codex or Claude Code. The installer uses Node.js. The archiving and search tools use the Python 3 standard library. [Installer instructions](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Try “I feel like talking about my week.” Choose a folder when you first have something you want to keep. A compatible AI with access to that folder can use it in a later chat. If you change tools, you can also give the new one a single Markdown entry you choose. Material discussed in chat goes through the AI service you use.

## If you want to leave something for loved ones

Keep an original recording with its story, even if the only person you have in mind is your future self. If you’d like someone to hear your stories after you’re gone, you can prepare a printable memoir or an offline card with selected recordings, and leave a copy with someone you trust. You decide who gets it and arrange the handoff yourself.

*Grandpa’s knock* is a fictional example of a card you could leave. Extract the ZIP, open `index.html`, look up “How did Grandpa knock?” and play the three knocks. A recipient can also give the ZIP to Codex with this skill and ask about just those stories. Each selected media file is included in full, and playback uses the recording you supply. [Hear the example](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [Download the card](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-en.zip) · [Preview](examples/knock-en.png)
