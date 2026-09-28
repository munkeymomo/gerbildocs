# Releasing GerbilDocs

Downloads live on SourceForge, the source lives on GitHub, and both carry the
same files. The GitHub build makes and publishes the release; SourceForge
copies it. This is the whole procedure; the one-time account setup is at the
end.

## Cut the release

Bump `version` in `pyproject.toml`. It is the single source:
`packaging/build.py`, `tools/make_release.py` and the build workflow all read
it. Set `API_VERSION` in `app/api.py`, `APP_VERSION` in `app/static/index.html`
and `AppVersion` in `packaging/installer.iss` to match (the version chip in the
header and the About box read the first two). Write the new section in
`CHANGELOG.md` and a `RELEASE-NOTES-<version>.md`; the release fails without
the notes, because they are its body.

Check it builds and runs locally first, with nothing from GerbilDocs running
(PyInstaller cannot replace a locked `.exe`):

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m app.selfcheck
.venv\Scripts\python.exe tools\make_release.py --install "..\GerbilDocs"
```

`--install` copies the built application over the folder you actually run it
from. Without it the build lands in `dist/` only, the copy on the desktop goes
on being the old one, and the next thing you notice is a bug in a version that
no longer exists.

## Publish the source and the release

The public repository is the source archive, so the two can never disagree.
Copy `release/<version>/gerbildocs-<version>-src.zip`'s contents over the
public checkout, commit the difference as Mark Isaacs
<munkeymomo@gmail.com>, and push `main`. Do not publish the working
repository: its history predates the rename and carries the old branding and
a work email address in every commit. The build workflow,
`.github/workflows/build.yml`, lives in the public repository and is edited
there.

Then on GitHub: **Actions → Build → Run workflow**, branch `main`, tick
**Publish a release**, and run it. About fifteen minutes later:

- the Linux tests, the Windows build, the installer and a smoke run have
  passed;
- the portable zip has been unzipped, **tagged as a browser download**, and
  `GerbilDocs.exe --check-window` has loaded the window's runtime from it
  (1.4.0 shipped a zip that failed exactly this way);
- release `v<version>` exists, titled "GerbilDocs <version>", with the notes
  as its body and these files:

| File | What it is |
|---|---|
| `GerbilDocs-<v>-setup.exe` | the installer |
| `GerbilDocs-<v>-win32.zip` | the portable application; unzip and run |
| `GerbilDocs-<v>-standalone.html` | the single file that runs in a browser |
| `gerbildocs-<v>-src.zip` | the source, MIT |
| `README.md` | the release notes, which SourceForge shows on the folder |
| `SHA256SUMS.txt` | one line per file above |

The job builds the release as a draft, attaches everything, and only then
publishes it. That order matters: SourceForge copies a release when it is
published and does not see files added afterwards. It refuses to run if the
release already exists (bump the version) or the notes are missing. Pushing a
`v<version>` tag does the same thing, but push **one tag at a time**: GitHub
starts no workflows at all for a push of more than three tags.

**The source archive is not the working tree.** `tools/make_release.py` lists
what it leaves out in `PRIVATE`: `HANDOFF.md`, `CLAUDE.md` and
`docs/PROMPT-ui-upgrade.md` are development notes that name the machine the
work was done on and its home-directory paths. Check that list before adding
anything of that kind to the repository.

MathJax (`app/static/vendor/mathjax/tex-svg-full.js`, about 2 MB) is fetched,
not authored, so it is excluded from the source archive and `README.md` tells
people to run `tools/fetch_mathjax.py`. It **is** inside the portable zip, so
equations render there with no network.

## SourceForge

The project's GitHub integration imports each published release into a folder
of its own. Once it appears, set the default downloads, because that is what
the big green button offers: click the **(i)** beside
`GerbilDocs-<v>-setup.exe` and tick **Windows**; click it beside
`GerbilDocs-<v>-standalone.html` and tick Mac, Linux and the rest. Without
them visitors are offered the code.

Delete the two "source code" archives GitHub adds to every release if the
import copied them; `gerbildocs-<v>-src.zip` is the same code.

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
