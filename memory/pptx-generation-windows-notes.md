---
name: pptx-generation-windows-notes
description: Environment quirks hit when building the Cafe Wi-Fi project presentation (.pptx) on this Windows machine
metadata: 
  node_type: memory
  type: project
  originSessionId: cb691773-5fdd-4626-a96b-2d61e3429997
  modified: 2026-08-25T17:54:43.235Z
---

Built a 15-slide `.pptx` presentation for the cafe-wifi project (Thai academic senior-project deck, coffee/teal palette, Tahoma font) via `pptxgenjs`. Several environment-specific problems came up that will recur on this machine for any future pptx work:

1. **No LibreOffice installed on this machine.** The pptx skill's `scripts/office/soffice.py` wrapper also fails outright here — it's written for a Linux sandbox and calls `socket.AF_UNIX`, which doesn't exist on native Windows Python, so it throws `AttributeError` before even checking for soffice.
   **Workaround:** Microsoft PowerPoint (Office ProPlus 2021) *is* installed. Use PowerShell COM automation instead to render slides to PNG for visual QA:
   ```powershell
   $ppt = New-Object -ComObject PowerPoint.Application
   $pres = $ppt.Presentations.Open($deckPath, $true, $false, $false)
   $pres.SaveAs($outDir, 18)  # 18 = ppSaveAsPNG, exports one PNG per slide
   $pres.Close(); $ppt.Quit()
   ```
   Exported filenames come out as Thai-localized `สไลด์N.PNG` — rename with a regex on the trailing number to get sortable `slide-NN.png`. This is actually higher-fidelity QA than LibreOffice since it's the real PowerPoint renderer.

2. **`scripts/office/validate.py` needs `defusedxml`, `lxml`, `Pillow` — not preinstalled** on this machine's Python (had to `pip install defusedxml lxml Pillow markitdown[pptx]` first). `markitdown` also isn't on PATH as a bare command; invoke as `python -m markitdown`.

3. **`validate.py` fails with `'charmap' codec can't decode byte ...`** on every slide when run normally on this machine — Windows Python defaults to cp1252 for file reads, and the script doesn't pass `encoding="utf-8"`. Fix: run with `PYTHONUTF8=1` env var prefixed, e.g. `PYTHONUTF8=1 python validate.py deck.pptx`. Same trick needed for `python -m markitdown`.

4. **Thai text + `charSpacing` (letter-spacing) in pptxgenjs breaks readability.** Thai script relies on tightly-composed combining marks; adding positive `charSpacing` (used for the usual small-caps "kicker" label styling) visibly pries the characters apart into an ugly, hard-to-read mess. Don't apply `charSpacing`/letter-spacing to any text box that contains Thai — leave it unset (0) for Thai headers/kickers/labels, even where an all-English deck would normally use it for a small-caps eyebrow label.

5. **Font choice for Thai on this machine:** Tahoma (ships with Windows, has `tahoma.ttf`/`tahomabd.ttf`) renders Thai correctly and is a safe pick for both body and headers. `fc-list` isn't available in the bash environment here (git-bash lacks fontconfig) — check installed fonts via `ls /c/Windows/Fonts` instead when verifying font availability for Thai/CJK work.

**Why this matters:** these are one-time environment facts (no LibreOffice, PowerPoint COM works, Python encoding default, missing pip packages) that would otherwise cost a full re-diagnosis cycle next time a pptx/artifact-rendering task comes up on this machine.
