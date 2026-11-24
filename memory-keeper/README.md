# memory-keeper · An AI chat companion

**Let your AI get to know you through everyday conversation.** [中文](README_CN.md)

With chat memory on, the AI picks up on experiences you describe, what matters to you and how you like to talk. It also has a voice of its own. Feedback helps it learn when to offer a candid opinion and when to listen.

> You once mentioned that rehearsing the first line helped before an interview. Next time the subject comes up, it can offer to play the interviewer and let you try your opening.

## Get started

In Codex, paste this request.

```text
Install the memory-keeper skill from https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Or run this in your project and select Codex or Claude Code. The installer uses Node.js. The archiving and search tools use the Python 3 standard library. [Installer instructions](https://github.com/vercel-labs/skills#install-a-skill)

```sh
npx skills add https://github.com/TingdeLiu/Tyndall-Skills/tree/main/memory-keeper
```

Choose a local folder and whether to enable automatic chat memory. Then talk naturally in any chat using this skill with access to that folder. You can say “Skip this part,” “Pause automatic memory” or “What made you think that about me?” Material used in chat goes through the AI service you choose.

## What carries over

| File | What it holds |
|---|---|
| `profile.md` | Your portrait, including preferences and the situations where they apply. |
| `SOUL.md` | The companion’s name, personality and habits it develops from your interactions. |
| `memories/` | Your experiences and original words, with optional photos, recordings and videos. |

Learned notes link to the recollection behind them. You can correct an impression, change the companion’s voice or pause saving.

<details>
<summary>Share selected stories with loved ones</summary>

Keep an original recording with its story, even if the only person you have in mind is your future self. If you’d like someone to hear your stories after you’re gone, you can prepare a printable memoir or an offline card with selected recordings, and leave a copy with someone you trust. You decide who gets it and arrange the handoff yourself.

*Grandpa’s knock* is a fictional example of a card you could leave. Extract the ZIP, open `index.html`, look up “How did Grandpa knock?” and play the three knocks. A recipient can also give the ZIP to Codex with this skill and ask about just those stories. Each selected media file is included in full, and playback uses the recording you supply. [Hear the example](https://cdn.jsdelivr.net/gh/TingdeLiu/Tyndall-Skills@cdada5c/memory-keeper/examples/knock.wav) · [Download the card](https://github.com/TingdeLiu/Tyndall-Skills/raw/refs/heads/main/memory-keeper/examples/knock-en.zip) · [Preview](examples/knock-en.png)

</details>
