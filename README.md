# DECtalk Studio 1.3

Multitrack singing editor using DECtalk, for Android (`android/`) and the web (`web/`). Both builds share one UI:
`android/assets/web/index.html`. `web/build_page.py` turns it into a self-contained page with DECtalk compiled to
WebAssembly (see web/ for how DECtalk's threads run as green threads in the browser).

New in 1.3
- DECtalk text export: `[:phoneme on][:np][d<41>ey<1270,32>...]`, optionally split into messages under a character limit.
  Timing is compensated for DECtalk's 6.4 ms frame rounding (frames = floor((ms + 4) / 6.4), each lasting 71 samples
  at 11,025 Hz), so a 2.7-minute test song stays within about 0.1 s.
- Split a part into left and right hand (follows each hand by continuity), at a note, or into single-note lines.
