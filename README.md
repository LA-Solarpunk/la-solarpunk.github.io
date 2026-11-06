# LA Solarpunk

A community hub for solarpunk ideas, projects, and organizing in Los
Angeles — where ecology, technology, and mutual aid grow together.

The site is plain Markdown plus a standalone `index.html` renderer
(tiny-markdown) with all page styles in `styles.css` (linked from
`index.html`): no database, no framework, no build step to install.
`index.html` renders `index.md` in the browser, and `index.md` is
generated — it is a list of every Markdown file in the repository.

## Build process

`scripts/build-index.py` (Python 3, standard library only) scans the
repository for Markdown files, reads each file's front-matter `title:`
(or first heading), sorts the entries newest first by their
`YYYY-MM-DD-` file-name prefix, and regenerates `index.md` in full:
a plain Markdown list of entries. There are no
marker comments wrapping the list. Entries are wikilinks —
`[[2026-06-21-westwood-greenway|Visiting the Westwood Greenway]]` —
not standard Markdown links, so the renderer in `index.html` navigates
to them in-page. `index.md` is generated, so do not edit it by hand.

Run it locally:

```sh
python3 scripts/build-index.py               # regenerate index.md
python3 scripts/build-index.py --site-dir _site   # also assemble _site/
```

The generated `index.md` is committed, and the GitHub Actions workflow
regenerates it on every push, so the published list never goes stale
and nobody has to update it by hand. `_site/` is build output (see
`.gitignore`) and is never committed.

## Publishing (GitHub Pages)

`.github/workflows/deploy.yml` runs on every push to `main` (and can be
triggered manually from the Actions tab):

1. **build** — checks out the repo, runs
   `python3 scripts/build-index.py --site-dir _site`, and uploads
   `_site/` (`index.html`, the generated `index.md`, every Markdown
   file, and any static assets) as the Pages artifact.
2. **deploy** — publishes that artifact with `actions/deploy-pages`.

One-time setup, in the repository's **Settings → Pages**: set
**Build and deployment → Source** to **GitHub Actions**. Without this
the workflow's deployments go nowhere. After that, publishing is just:
add or edit a Markdown file, push to `main`, wait about a minute.

## Adding a post

Create a Markdown file at the repository root named
`YYYY-MM-DD-your-post-title.md`, for example
`2026-06-21-westwood-greenway.md`, starting with front matter:

```yaml
---
title: "Your Post Title"
date: 2026-06-21
description: "A short description of the post."
---
```

`index.html` shows a note's front matter at the top of the note: a
`title` is rendered as `<h1>{{title}}</h1>`, and a `date`, when present,
as `<h3>{{date}}</h3>` directly underneath it. Notes without those
fields get no header.

Write the post in standard Markdown below the front matter, commit,
and push. The next workflow run picks the file up automatically and it
appears in the `index.md` list — no other file needs editing.

## Images and other embeds

Use wikilink embed style, with the alt/caption text after the pipe:

```markdown
![[charles_teaching.jpg|charles teaching]]
```

Put the image file in the repository (at the root, or in a subfolder
the embed path points into) and reference it by that path. The same
`![[ ]]` form is used for video and audio files. Standard Markdown
images and `<img>` tags are not used in this site — the build fails if
it finds one, or an embed pointing at a file that does not exist.
