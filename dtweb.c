/* WebAssembly entry point: the browser calls dt_api() for every engine request. */
#include "ttsapi.h"
#include <stdio.h>
static LPTTS_HANDLE_T h;
/* op 0: start engine. op 1: render text b to WAV file a. op 2: write pronunciation log of b to a */
__attribute__((export_name("dt_api"))) int dt_api(int op, char *a, char *b) {
  switch (op) {
  case 0:
    return TextToSpeechStartup(&h, WAVE_MAPPER, DO_NOT_USE_AUDIO_DEVICE, NULL, 0);
  case 1:
    if (TextToSpeechOpenWaveOutFile(h, a, WAVE_FORMAT_1M16) != MMSYSERR_NOERROR) return -1;
    TextToSpeechSpeak(h, b, TTS_FORCE);
    TextToSpeechSync(h);
    TextToSpeechCloseWaveOutFile(h);
    return 0;
  case 2:
    remove(a);
    if (TextToSpeechOpenLogFile(h, a, 18) != MMSYSERR_NOERROR) return -1;
    TextToSpeechOpenWaveOutFile(h, "discard.wav", WAVE_FORMAT_1M16);
    TextToSpeechSpeak(h, b, TTS_FORCE);
    TextToSpeechSync(h);
    TextToSpeechCloseWaveOutFile(h);
    TextToSpeechCloseLogFile(h);
    return 0;
  }
  return -2;
}
