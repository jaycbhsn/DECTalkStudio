/* The browser build has no audio device: DECtalk only writes WAV files, and the page plays them.
   These replace the Linux sound-card layer (linux_audio.c). */
#include "dectalkf.h"
#include "port.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "kernel.h"
#include "opthread.h"
#include "mmalloc.h"
#include "playaudd.h"
#include "playaud.h"
#include "tts.h"
#include "linux_audio.h"

LONG OSS_WaveInit(void) { return 0; }
UINT16 waveOutGetNumDevs() { return 1; }
UINT32 waveOutGetDevCaps(UINT16 id, LPWAVEOUTCAPS c, UINT32 n) { if (c) memset(c, 0, n); return MMSYSERR_NOERROR; }
UINT16 waveOutOpen(LPHWAVEOUT h, UINT16 id, const LPWAVEFORMATEX f, void (*cb)(void *, unsigned int, unsigned int, long, long), DWORD inst, DWORD fl) { return MMSYSERR_ALLOCATED; }
UINT16 waveOutClose(HWAVEOUT h) { return MMSYSERR_NOERROR; }
UINT32 waveOutPrepareHeader(HWAVEOUT h, WAVEHDR *w, UINT32 n) { return MMSYSERR_NOERROR; }
UINT32 waveOutUnprepareHeader(HWAVEOUT h, WAVEHDR *w, UINT32 n) { return MMSYSERR_NOERROR; }
UINT32 waveOutWrite(HWAVEOUT h, WAVEHDR *w, UINT32 n) { return MMSYSERR_NOERROR; }
UINT16 waveOutPause(HWAVEOUT h) { return MMSYSERR_NOERROR; }
UINT16 waveOutRestart(HWAVEOUT h) { return MMSYSERR_NOERROR; }
UINT16 waveOutReset(HWAVEOUT h) { return MMSYSERR_NOERROR; }
UINT16 waveOutGetVolume(HWAVEOUT h, LPDWORD v) { if (v) *v = 0xFFFFFFFF; return MMSYSERR_NOERROR; }
UINT16 waveOutSetVolume(HWAVEOUT h, DWORD v) { return MMSYSERR_NOERROR; }
UINT16 waveOutGetPosition(HWAVEOUT h, LPMMTIME t, UINT16 n) { if (t) memset(t, 0, n); return MMSYSERR_NOERROR; }
UINT32 waveOutGetID(HWAVEOUT h, UINT32 *id) { if (id) *id = 0; return MMSYSERR_NOERROR; }

/* "common" globals from DECtalk headers, defined once (wasm-ld does not merge common symbols) */
int radius = 0, noisec = 0, ranmul = 0, ranadd = 0, temp = 0;

char *mktemp(char *t) { static int n; size_t l = strlen(t); for (size_t i = l; i > 0 && t[i - 1] == 'X'; i--) t[i - 1] = '0' + (n++ % 10); return t; }
