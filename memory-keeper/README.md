# memory-keeper · An AI chat companion

**Help your AI get to know you, one conversation at a time.** [中文](README_CN.md)

Pick a line from a conversation that you want it to remember, or let it interview you. When a related subject comes up in a new chat, it can find your original words and pick up the thread.

> “Interview me, one question at a time. When we finish, let me choose what to keep for next time.”

## Get started

In Codex, paste this request.

```text
Install the memory-keeper skill from https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Or run this in your project and select Codex or Claude Code. The installer uses Node.js. The archiving and search tools use the Python 3 standard library. [Installer instructions](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Start chatting as soon as the skill is installed. Choose your folder the first time you want to keep a story or set a lasting preference. Use the skill in a fresh chat with access to the same folder to pick up where you left off. Your stories live in Markdown files alongside any photos, recordings and videos you keep. You can edit your companion’s personality in `SOUL.md`. Material discussed in chat goes through the AI service you use.

## Try it with a conversation you already had

Paste an excerpt and say “Help me pick what I'd like to come back to.” The AI shows you your own words and lets you choose which parts to save. Later, ask “What did I actually say?” to find the original note. You can correct it at any time.

<details>
<summary>Share selected stories with loved ones</summary>

Keep an original recording with its story, even if the only person you have in mind is your future self. If you’d like someone to hear your stories after you’re gone, you can prepare a printable memoir or an offline card with selected recordings, and leave a copy with someone you trust. You decide who gets it and arrange the handoff yourself.

*Grandpa’s knock* is a fictional example of a card you could leave. Extract the ZIP, open `index.html`, look up “How did Grandpa knock?” and play the three knocks. A recipient can also give the ZIP to Codex with this skill and ask about just those stories. Each selected media file is included in full, and playback uses the recording you supply. [Hear the example](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [Download the card](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-en.zip) · [Preview](examples/knock-en.png)

</details>
