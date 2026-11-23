// Runs from file:// after extraction. All excerpts and links come from this page.
const form = document.getElementById("ask");
const field = document.getElementById("q");
const results = document.getElementById("matches");
const stop = new Set(("a an the of in on to at and or do did does what how why where when who is was were " +
    "would can could his her their me my tell about " +
    "什么 怎么 如何 为什么 这个 那个 他们 她们 我们 一下 有没有 是不是 时候 请问 知道 告诉").split(/\s+/));

function terms(text) {
    const words = new Set();
    for (const part of text.toLowerCase().normalize("NFKC").match(/[\p{Script=Han}]+|[\p{L}\p{N}]+/gu) || []) {
        if (/\p{Script=Han}/u.test(part)) {
            for (const chunk of part.split(/为什么|是什么|怎么|如何|什么|有没有|是不是|的时候|请问|告诉我|[的是了呢吗呀在她他我]/u)) {
                if (chunk.length === 1) words.add(chunk);
                for (let i = 1; i < chunk.length; i++) words.add(chunk.slice(i - 1, i + 1));
            }
        } else if (!stop.has(part)) {
            words.add(part.length > 4 ? part.replace(/(?:ed|ing|s)$/, "") : part);
        }
    }
    return [...words].filter(word => !stop.has(word));
}

function linkTo(id, label) {
    const link = document.createElement("a");
    link.href = "#" + id;
    link.textContent = label;
    return link;
}

const excerpts = Array.from(document.querySelectorAll("[data-passage]"), node => {
    const story = node.closest("article");
    const title = story.querySelector(".story-title").textContent;
    return {node, story, title, words: new Set(terms(node.textContent)), titleWords: new Set(terms(title))};
});

form.addEventListener("submit", event => {
    event.preventDefault();
    results.replaceChildren();
    const query = terms(field.value);
    const ranked = excerpts.map(entry => {
        const bodyHits = query.filter(word => entry.words.has(word)).length;
        const titleHits = query.filter(word => entry.titleWords.has(word)).length;
        // A title-only match leads to the opening paragraph once.
        const score = bodyHits || entry.node.id.endsWith("-p1") ? 3 * bodyHits + titleHits : 0;
        return {entry, score};
    }).filter(item => item.score > 0).sort((a, b) => b.score - a.score);
    if (!ranked.length) {
        results.textContent = form.dataset.empty;
        return;
    }
    for (const {entry} of ranked.slice(0, 5)) {
        const row = document.createElement("p");
        const number = entry.node.id.split("-p")[1];
        row.append(linkTo(entry.node.id, entry.title + " · ¶" + number), " · ", entry.node.textContent);
        const media = entry.story.querySelector("figure");
        if (media) row.append(" · ", linkTo(media.id, form.dataset.originals));
        results.append(row);
    }
});
field.addEventListener("input", () => results.replaceChildren());
