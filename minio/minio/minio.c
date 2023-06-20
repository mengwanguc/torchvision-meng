/* Author:  Gus Waldspurger

   Implementation of a MinIO file cache.
   */

#include "minio.h"

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

#include "../include/uthash.h"


/* ------------------------ */
/*   REPLACEMENT POLICIES   */
/* ------------------------ */

typedef uint64_t policy_func_t(cache_t *, void *, size_t);

/* FIFO cache replacement policy. */
static uint64_t
policy_FIFO(cache_t *cache, void *item, size_t size)
{
   return -1;
}

/* MinIO cache replacement policy. */
static uint64_t
policy_MINIO(cache_t *cache, void *item, size_t size)
{
   return -1;
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
   filesystem at FILEPATH. If the cached file is greater than MAX_SIZE bytes, -1
   is returned. Otherwise, all data is copied and 0 is returned on success. */
int
cache_read(cache_t *cache, char *filepath, void *data, uint64_t max_size)
{
   /* Check if the file is cached. */
   hash_entry_t *entry = NULL;
   HASH_FIND_STR(cache->ht, filepath, entry);
   if (entry != NULL) {
      /* Don't overflow the buffer. */
      if (entry->size > max_size) {
         return -1;
      }
      memcpy(data, entry->ptr, entry->size);

      return 0;
   }

   /* Open the file in DIRECT mode. */
   int fd = open(filepath, O_RDONLY | __O_DIRECT);
   if (fd == -1 ) {
      return -1;
   }
   FILE *file = fdopen(fd, "r");

   /* Ensure the size of the file is OK. */
   fseek(file, 0L, SEEK_END);
   size_t size = ftell(file);
   if (size > max_size) {
      fclose(file);
      return -1;
   }
   rewind(file);

   /* Read into data and cache the data if it'll fit. */
   read(fd, data, size);
   if (size <= cache->size - cache->used) {
      /* Make an entry. */
      entry = malloc(sizeof(hash_entry_t));
      if (entry == NULL) {
         return -1;
      }
      strncpy(entry->filepath, filepath, MAX_PATH_LENGTH);
      entry->size = size;
      entry->hh;

      /* Copy data to the cache. */
      entry->ptr = cache->data + cache->used;
      memcpy(entry->ptr, data, size);
      cache->used += size;

      /* Place the entry into the hash table. */
      HASH_ADD_STR(cache->ht, filepath, entry);
   }

   return 0;
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

   /* Initialize the hash table. */
   cache->ht = NULL;

   /* Allocate the cache's memory. */
   if ((cache->data = malloc(size)) == NULL) {
      fprintf(stderr, "Failed to allocate the cache's memory (do you have permission to mlock?). Aborting.\n");
      return -1;
   }

   /* Pin the cache's memory. */
   if (mlock(cache->data, size) != 0) {
      fprintf(stderr, "Failed to pin the cache's memory. Aborting.\n");
      return -1;
   }

   return 0;
}