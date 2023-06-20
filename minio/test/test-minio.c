/* Author:  Gus Waldspurger

   MinIO file cache tests.
   */

#include "../minio/minio.h"

#include <stdio.h>
#include <time.h>
#include <stdbool.h>
#include <assert.h>

#define KB (1024)
#define MB (KB * KB)
#define GB (KB * KB * KB)

#define CACHE_SIZE (16 * MB)
#define MAX_SIZE (32 * MB)
#define N_FILES (3)

/* Returns access time in nanoseconds. */
long
timed_access(cache_t *cache, char *filepath, void *data, size_t max_size)
{
    struct timespec start, end;

    clock_gettime(CLOCK_REALTIME, &start);
    assert(cache_read(cache, filepath, data, max_size) == 0);
    clock_gettime(CLOCK_REALTIME, &end);

    return (start.tv_nsec + start.tv_sec * 1e9) - (end.tv_nsec + end.tv_sec * 1e9);
}

/* Test that hot accesses for items that fit in the cache are faster than their
   cold accesses, and that uncached items are approximately the same. */
void
test_timing()
{
    /* Access times in nanoseconds. */
    long times_hot[N_FILES];
    long times_cold[N_FILES];

    /* Test data. */
    char filepaths[N_FILES][MAX_PATH_LENGTH] = {
        "./test-images/2MB.bmp",
        "./test-images/4MB.bmp",
        "./test-images/20MB.bmp"
    };

    bool should_cache[N_FILES] = {
        true,
        true,
        false
    };

    /* Where we're reading the file into. */
    uint8_t *data = malloc(MAX_SIZE);
    assert(data != NULL);

    /* Cache being tested. */
    cache_t cache;
    assert(cache_init(&cache, CACHE_SIZE, POLICY_MINIO) == 0);

    /* Cold accesses. */
    for (int i = 0; i < N_FILES; i++) {
        times_cold[i] = timed_access(&cache, filepaths[i], data, MAX_SIZE);
    }

    /* Hot accesses. */
    for (int i = 0; i < N_FILES; i++) {
        times_hot[i] = timed_access(&cache, filepaths[i], data, MAX_SIZE);
    }

    /* Check timing. */
    for (int i = 0; i < N_FILES; i++) {
        double speedup = (1e-9 * times_cold[i]) / (1e-9 * times_hot[i]);
        printf("Speedup for item %d is %.02lfx.\n", i, speedup);
        if (should_cache[i]) {
            assert(speedup >= 2);
        } else {
            assert(speedup < 2);
        }
    }
}

int
main(int argc, char **argv)
{
    test_timing();
}
