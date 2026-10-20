/* Cooperative green threads for DECtalk in WebAssembly.
   DECtalk's pipeline threads take turns on the browser's single thread: whenever one would
   block (mutex, condition wait, sleep), it calls fb_yield(), which the JavaScript host turns
   into an Asyncify stack switch to the next thread. */
#include <pthread.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
struct sched_param { int sched_priority; };

#define IMPORT(n) __attribute__((import_module("env"), import_name(n)))
IMPORT("fb_yield") void fb_yield(void);
IMPORT("fb_exit") void fb_exit(void);
IMPORT("fb_spawn") int fb_spawn(void *(*fn)(void *), void *arg);
IMPORT("fb_current") int fb_current(void);
IMPORT("fb_done") int fb_done(int id);

/* host calls this to start a green thread's body */
__attribute__((export_name("fb_trampoline"))) void fb_trampoline(void *(*fn)(void *), void *arg) { fn(arg); }

static double now_ms(void) { struct timespec t; clock_gettime(CLOCK_REALTIME, &t); return t.tv_sec * 1000.0 + t.tv_nsec / 1e6; }

/* threads */
int fb_pthread_create(pthread_t *t, const pthread_attr_t *a, void *(*fn)(void *), void *arg) { *t = (pthread_t)(long)fb_spawn(fn, arg); return 0; }
int fb_pthread_join(pthread_t t, void **ret) { while (!fb_done((int)(long)t)) fb_yield(); if (ret) *ret = 0; return 0; }
int fb_pthread_detach(pthread_t t) { return 0; }
void fb_pthread_exit(void *r) { fb_exit(); for (;;) fb_yield(); }
pthread_t fb_pthread_self(void) { return (pthread_t)(long)fb_current(); }
int fb_pthread_attr_init(pthread_attr_t *a) { return 0; }
int fb_pthread_attr_destroy(pthread_attr_t *a) { return 0; }
int fb_pthread_attr_setstacksize(pthread_attr_t *a, size_t s) { return 0; }
int fb_pthread_attr_setschedpolicy(pthread_attr_t *a, int p) { return 0; }
int fb_pthread_getschedparam(pthread_t t, int *pol, struct sched_param *p) { if (pol) *pol = 0; if (p) p->sched_priority = 0; return 0; }
int fb_pthread_setschedparam(pthread_t t, int pol, const struct sched_param *p) { return 0; }
int fb_sched_yield(void) { fb_yield(); return 0; }

/* mutex: [0]=locked [1]=owner [2]=depth (recursive-safe) */
int fb_pthread_mutexattr_init(pthread_mutexattr_t *a) { return 0; }
int fb_pthread_mutexattr_destroy(pthread_mutexattr_t *a) { return 0; }
int fb_pthread_mutexattr_settype(pthread_mutexattr_t *a, int t) { return 0; }
int fb_pthread_mutex_init(pthread_mutex_t *m, const pthread_mutexattr_t *a) { int *p = (int *)m; p[0] = 0; p[1] = -1; p[2] = 0; return 0; }
int fb_pthread_mutex_destroy(pthread_mutex_t *m) { return 0; }
int fb_pthread_mutex_lock(pthread_mutex_t *m) {
  int *p = (int *)m, me = fb_current();
  if (p[0] && p[1] == me) { p[2]++; return 0; }
  while (p[0]) fb_yield();
  p[0] = 1; p[1] = me; p[2] = 1; return 0;
}
int fb_pthread_mutex_trylock(pthread_mutex_t *m) {
  int *p = (int *)m, me = fb_current();
  if (p[0] && p[1] != me) return EBUSY;
  if (p[0]) { p[2]++; return 0; }
  p[0] = 1; p[1] = me; p[2] = 1; return 0;
}
int fb_pthread_mutex_unlock(pthread_mutex_t *m) { int *p = (int *)m; if (--p[2] <= 0) { p[0] = 0; p[1] = -1; p[2] = 0; } return 0; }

/* condition: [0]=generation, bumped on signal; waiters resume when it changes */
int fb_pthread_cond_init(pthread_cond_t *c, const void *a) { ((int *)c)[0] = 0; return 0; }
int fb_pthread_cond_destroy(pthread_cond_t *c) { return 0; }
int fb_pthread_cond_signal(pthread_cond_t *c) { ((int *)c)[0]++; return 0; }
int fb_pthread_cond_broadcast(pthread_cond_t *c) { ((int *)c)[0]++; return 0; }
int fb_pthread_cond_wait(pthread_cond_t *c, pthread_mutex_t *m) {
  int *g = (int *)c, s = g[0], *mp = (int *)m, depth = mp[2];
  mp[2] = 1; fb_pthread_mutex_unlock(m);
  while (g[0] == s) fb_yield();
  fb_pthread_mutex_lock(m); mp[2] = depth; return 0;
}
int fb_pthread_cond_timedwait(pthread_cond_t *c, pthread_mutex_t *m, const struct timespec *abst) {
  int *g = (int *)c, s = g[0], *mp = (int *)m, depth = mp[2], r = 0;
  double deadline = abst->tv_sec * 1000.0 + abst->tv_nsec / 1e6;
  mp[2] = 1; fb_pthread_mutex_unlock(m);
  while (g[0] == s) { if (now_ms() >= deadline) { r = ETIMEDOUT; break; } fb_yield(); }
  fb_pthread_mutex_lock(m); mp[2] = depth; return r;
}

/* sleeping just lets the other threads run until the time has passed */
int fb_nanosleep(const struct timespec *req, struct timespec *rem) {
  double until = now_ms() + req->tv_sec * 1000.0 + req->tv_nsec / 1e6;
  do fb_yield(); while (now_ms() < until);
  if (rem) { rem->tv_sec = 0; rem->tv_nsec = 0; }
  return 0;
}
int fb_usleep(unsigned us) { struct timespec t = { us / 1000000, (us % 1000000) * 1000 }; return fb_nanosleep(&t, 0); }
unsigned fb_sleep(unsigned s) { struct timespec t = { s, 0 }; fb_nanosleep(&t, 0); return 0; }

/* read-only "mapping" of the dictionary: read the whole file into memory */
void *fb_mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
  char *buf = malloc(len); if (!buf) return (void *)-1;
  off_t cur = lseek(fd, 0, SEEK_CUR); lseek(fd, off, SEEK_SET);
  size_t got = 0; ssize_t n;
  while (got < len && (n = read(fd, buf + got, len - got)) > 0) got += n;
  memset(buf + got, 0, len - got); lseek(fd, cur, SEEK_SET);
  return buf;
}
int fb_munmap(void *addr, size_t len) { free(addr); return 0; }
