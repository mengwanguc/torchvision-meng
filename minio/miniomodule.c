/* Author:  Gus Waldspurger
   Date:    June 16, 2023.

   Implementation of a MinIO file cache.
   */

#include "miniomodule.h"

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <sys/mman.h>

#include <include/uthash.h>

/* ------------------------ */
/*   REPLACEMENT POLICIES   */
/* ------------------------ */

typedef uint64_t (*policy_func_t(cache_t *, void *, size_t));

/* FIFO cache replacement policy. */
static uint64_t
policy_FIFO(cache_t *cache, void *item, size_t size)
{
   return NULL;
}

/* MinIO cache replacement policy. */
static uint64_t
policy_MINIO(cache_t *cache, void *item, size_t size)
{
   static uint8_t *next;

   return NULL;
}

/* Policy table converts from policy_t enum to policy function. */
static policy_func_t *policy_table[N_POLICIES] = {
   policy_FIFO,
   policy_MINIO
};


/* ------------- */
/*   INTERFACE   */
/* ------------- */

/* Read an item from CACHE into DATA, indexed by FILEPATH, and located on the
   filesystem at FILEPATH. If the cached file is greater than MAX_SIZE bytes,
   DATA is filled with the first MAX_SIZE bytes, and -1 is returned. Otherwise,
   0 is returned on success. */
int
cache_get(cache_t *cache, char *filepath, void *data, uint64_t max_size)
{
   /* TODO: use direct IO to read in the file, to bypass the page cache. */
   return NULL;
}

/* Initialize a cache CACHE with SIZE bytes and POLICY replacement policy. On
   success, 0 is returned. On failure, -1 is returned. */
int
cache_init(cache_t *cache, size_t size, policy_t policy)
{
   /* Cache configuration. */
   cache->size = size;
   cache->used = 0;
   cache->policy = policy;

   /* TODO: initialize the filename -> void * hash table. */

   /* Allocate the cache's memory. */
   if ((cache->data = malloc(size)) == NULL) {
      fprintf(stderr, "Failed to allocate the cache's memory. Aborting.\n");
      return -1;
   }

   /* Pin the cache's memory. */
   if (mlock(cache->data, size) != 0) {
      fprintf(stderr, "Failed to pin the cache's memory. Aborting.\n");
      return -1;
   }

   return 0;
}