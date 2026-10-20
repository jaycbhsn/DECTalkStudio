/* Force-included into every DECtalk file for the WebAssembly build: redirects threading calls
   to cooperative green threads (fiber.c) and file mapping to a read-into-memory version. */
#ifndef FB_H
#define FB_H
#define pthread_create fb_pthread_create
#define pthread_join fb_pthread_join
#define pthread_detach fb_pthread_detach
#define pthread_exit fb_pthread_exit
#define pthread_self fb_pthread_self
#define pthread_attr_init fb_pthread_attr_init
#define pthread_attr_destroy fb_pthread_attr_destroy
#define pthread_attr_setstacksize fb_pthread_attr_setstacksize
#define pthread_attr_setschedpolicy fb_pthread_attr_setschedpolicy
#define pthread_getschedparam fb_pthread_getschedparam
#define pthread_setschedparam fb_pthread_setschedparam
#define pthread_mutex_init fb_pthread_mutex_init
#define pthread_mutex_destroy fb_pthread_mutex_destroy
#define pthread_mutex_lock fb_pthread_mutex_lock
#define pthread_mutex_trylock fb_pthread_mutex_trylock
#define pthread_mutex_unlock fb_pthread_mutex_unlock
#define pthread_mutexattr_init fb_pthread_mutexattr_init
#define pthread_mutexattr_destroy fb_pthread_mutexattr_destroy
#define pthread_mutexattr_settype fb_pthread_mutexattr_settype
#define pthread_cond_init fb_pthread_cond_init
#define pthread_cond_destroy fb_pthread_cond_destroy
#define pthread_cond_wait fb_pthread_cond_wait
#define pthread_cond_timedwait fb_pthread_cond_timedwait
#define pthread_cond_signal fb_pthread_cond_signal
#define pthread_cond_broadcast fb_pthread_cond_broadcast
#define sched_yield fb_sched_yield
#define nanosleep fb_nanosleep
#define usleep fb_usleep
#define sleep fb_sleep
#define mmap fb_mmap
#define munmap fb_munmap
#include <time.h>
#include <sys/types.h>
#ifndef FB_SCHED_PARAM
#define FB_SCHED_PARAM
struct sched_param { int sched_priority; };
#endif
#ifndef SCHED_OTHER
#define SCHED_OTHER 0
#define SCHED_FIFO 1
#define SCHED_RR 2
#endif
#endif
