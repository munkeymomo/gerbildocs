# Releasing GerbilDocs

Downloads live on SourceForge, the source lives on GitHub, and both carry the
same files. This is the whole procedure; the one-time account setup is at the
end.

## Cut the release

Bump `version` in `pyproject.toml` — it is the single source, and
`packaging/build.py`, the installer script and `tools/make_release.py` all read
it. Set `API_VERSION` in `app/api.py` and `APP_VERSION` in
`app/static/index.html` to match (the version chip in the header and the About
box read them). Write the new section in `CHANGELOG.md` and a
`RELEASE-NOTES-<version>.md`.

Then, with nothing from GerbilDocs running (PyInstaller cannot replace a
locked `.exe`):

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m app.selfcheck
.venv\Scripts\python.exe tools\make_release.py --install "..\GerbilDocs"
```

`--install` copies the built application over the folder you actually run it
from. Without it the build lands in `dist/` only, the copy on the desktop goes
on being the old one, and the next thing you notice is a bug in a version that
no longer exists. Leave the flag off only when building for somebody else.

That leaves `release/<version>/`:

| File | What it is |
|---|---|
| `GerbilDocs-<v>-win32.zip` | the portable application; unzip and run |
| `GerbilDocs-<v>-standalone.html` | the single file that runs in a browser |
| `gerbildocs-<v>-src.zip` | the source, MIT |
| `README.md` | the release notes, which SourceForge shows on the folder |
| `SHA256SUMS.txt` | one line per file |

**The source archive is not the working tree.** `tools/make_release.py` lists
what it leaves out in `PRIVATE`: `HANDOFF.md`, `CLAUDE.md` and
`docs/PROMPT-ui-upgrade.md` are development notes that name the machine the
work was done on and its home-directory paths. Check that list before adding
anything of that kind to the repository, and run the script once and read its
last few lines — it prints what it excluded.

MathJax (`app/static/vendor/mathjax/tex-svg-full.js`, about 2 MB) is fetched,
not authored, so it is excluded from the source archive and `README.md` tells
people to run `tools/fetch_mathjax.py`. It **is** inside the portable zip, so
equations render there with no network.

## Upload to SourceForge

Files → *Add Folder*, named for the version. Upload the five files into it.
SourceForge renders the folder's `README.md` as the release notes underneath
the file list, so it is worth having.

Then set the default download: click the **(i)** beside
`GerbilDocs-<v>-win32.zip`, and under *Default Download For* tick **Windows**.
That is what the big green button on the project page offers, and without it
visitors are offered the first file alphabetically.

## Publish the source on GitHub

The public repository is the source archive, so the two can never disagree.
Unpack the archive somewhere outside the working tree, initialise it there and
push that. Do not publish the working repository: its history predates the
rename and carries the old branding and a work email address in every commit.

```
git init
git config user.name "Mark Isaacs"
git config user.email "munkeymomo@gmail.com"
git add -A
git commit -m "GerbilDocs <version>"
git tag -a v<version> -m "GerbilDocs <version>"
git remote add origin https://github.com/<you>/gerbildocs.git
git push -u origin main --tags
```

Then make a GitHub release from the tag, paste `RELEASE-NOTES-<version>.md`
into the body, and attach the same files. `.github/workflows/build.yml` builds
Windows on every push once the repository exists.

For later releases, copy the new source archive over the public checkout,
commit the difference, and tag again.

## One-time: creating the SourceForge project

Sign in, then *Create* a project.

- **Name** GerbilDocs, which gives `sourceforge.net/projects/gerbildocs/` if it
  is free.
- **Summary**, the one line shown in search results:
  *Write papers, reports and grant applications with real pages. Free and open
  source.*
- **Licence** MIT.
- **Categories** Office/Business → Word Processors; Scientific/Engineering;
  Intended Audience → Science/Research; Operating System → Windows; Programming
  Language → Python, JavaScript; User Interface → Web-based.
- **Features** keep Files and Tickets; the Wiki, Blog, Forum and Git mirror are
  not needed while the source is on GitHub.

On the project page add the description, the screenshots from `docs/media/`, a
link to the GitHub repository and one to the Ko-fi page.

## A note on signing

The build is unsigned, so Windows SmartScreen warns the first time anyone runs
it, and the download will be flagged until enough people have run it. A code
signing certificate (an OV certificate is the cheap option, an EV one clears
SmartScreen immediately) is the only real fix. `README.md` and the release
notes both tell people what the warning is and how to get past it.
