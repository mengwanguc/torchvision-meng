/* Author:  Gus Waldspurger
   Date:    June 16, 2023.

   Implementation of a MinIO cache.
   */

#include "miniomodule.h"

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>


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

/* Problems/TODO

   Not all images are going to be the same size, so how do we decide which ones
   to cache without already knowing all of their sizes?

*/


/* Read an item from the cache CACHE into DATA. */
bool
cache_get(cache_t *cache, void *data)
{
   return NULL;
}

/* Initialize a cache CACHE with SIZE bytes and POLICY replacement policy. */
bool
cache_init(cache_t *cache, size_t size, policy_t policy)
{
   return NULL;
}