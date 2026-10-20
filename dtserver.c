/* DECtalk render server: reads "outfile.wav<TAB>text" lines on stdin,
   renders each to a WAV file, replies "OK" or "ERR" on stdout. */
#include "ttsapi.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

/* replies go on a private copy of stdout; DECtalk itself echoes logs to stdout, which is silenced */
static FILE *proto;

int main(int argc, char **argv) {
  LPTTS_HANDLE_T h = NULL;
  static char line[1 << 20];
  proto = fdopen(dup(1), "w");
  if (!freopen("/dev/null", "w", stdout)) return 1;
  int st = TextToSpeechStartup(&h, WAVE_MAPPER, DO_NOT_USE_AUDIO_DEVICE, NULL, 0);
  if (st != MMSYSERR_NOERROR) { fprintf(proto, "FAIL %d\n", st); fflush(proto); return 1; }
  fprintf(proto, "READY\n"); fflush(proto);
  while (fgets(line, sizeof line, stdin)) {
    size_t n = strlen(line);
    while (n && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
    if (!strcmp(line, "QUIT")) break;
    /* PHON<TAB>logfile<TAB>flags<TAB>text : log DECtalk's own pronunciation of text */
    if (!strncmp(line, "PHON\t", 5)) {
      char *lf = line + 5, *fl = strchr(lf, '\t'), *tx;
      if (!fl || !(tx = strchr(fl + 1, '\t'))) { fprintf(proto, "ERR\n"); fflush(proto); continue; }
      *fl++ = 0; *tx++ = 0;
      remove(lf);
      if (TextToSpeechOpenLogFile(h, lf, (DWORD)atoi(fl)) != MMSYSERR_NOERROR) { fprintf(proto, "ERR\n"); fflush(proto); continue; }
      TextToSpeechOpenWaveOutFile(h, "/dev/null", WAVE_FORMAT_1M16);
      TextToSpeechSpeak(h, tx, TTS_FORCE);
      TextToSpeechSync(h);
      TextToSpeechCloseWaveOutFile(h);
      TextToSpeechCloseLogFile(h);
      fprintf(proto, "OK\n"); fflush(proto); continue;
    }
    char *tab = strchr(line, '\t');
    if (!tab) { fprintf(proto, "ERR\n"); fflush(proto); continue; }
    *tab = 0;
    if (TextToSpeechOpenWaveOutFile(h, line, WAVE_FORMAT_1M16) != MMSYSERR_NOERROR) {
      fprintf(proto, "ERR\n"); fflush(proto); continue;
    }
    TextToSpeechSpeak(h, tab + 1, TTS_FORCE);
    TextToSpeechSync(h);
    TextToSpeechCloseWaveOutFile(h);
    fprintf(proto, "OK\n"); fflush(proto);
  }
  TextToSpeechShutdown(h);
  return 0;
}
