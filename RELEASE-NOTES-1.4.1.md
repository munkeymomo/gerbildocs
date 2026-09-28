# GerbilDocs 1.4.1

A fix for the portable Windows zip, which wouldn't start when it was
downloaded. Everything else is as 1.4.0.

## Fixed

**The portable zip now starts after a download.** When you unzip a download
with Windows Explorer, every file inside is tagged as coming from the
internet, and Windows then refuses to load the DLLs the app's window needs.
1.4.0 stopped at once with "Failed to resolve Python.Runtime.Loader.Initialize".
1.4.1 clears that tag from its own files when it starts.

If you already have the 1.4.0 zip, you don't need to download it again:
right-click the zip, choose **Properties**, tick **Unblock**, click **OK**,
then unzip it again.

## Also new

- If the app's window can't open for any other reason, GerbilDocs opens in
  your web browser instead of showing an error. A small box stays open while
  you work; close it to close GerbilDocs.
- Every release is now tested as a downloaded zip before it is published.

## Files

- `GerbilDocs-1.4.1-setup.exe`: the Windows installer. The easiest way in.
- `GerbilDocs-1.4.1-win32.zip`: the portable application. Unzip it anywhere
  and run `GerbilDocs.exe`. It starts empty. Your documents are kept in
  `Documents\GerbilDocs` and your library in your user profile, never in the
  application folder.
- `GerbilDocs-1.4.1-standalone.html`: a single-file browser version with
  nothing to install. It opens on an invented example document.
- `gerbildocs-1.4.1-src.zip`: the source code, MIT licensed.
- `SHA256SUMS.txt`: checksums for all of the above.

## Known limitations

- The Windows build isn't code-signed, so SmartScreen warns on the first
  run. Choose "More info", then "Run anyway".
- Only Windows is built and tested.
