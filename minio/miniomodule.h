/* Author:  Gus Waldspurger
   Date:    June 16, 2023.

   Implementation of a MinIO file cache.
   */

#ifndef __MINIO_MODULE_H_
#define __MINIO_MODULE_H_

#include <stdlib.h>

/* Cache replacement policy. */
typedef enum {
    POLICY_FIFO,
    POLICY_MINIO,
    N_POLICIES
} policy_t;

/* TODO find a hash table library to use. */
typedef int hash_t;

/* Cache. */
typedef struct {
    /* Configuration. */
    policy_t policy;    /* Replacement policy. Only MinIO supported. */
    size_t   size;      /* Size of cache in bytes. */
    size_t   used;      /* Number of bytes cached. */

    /* State. */
    uint8_t *data;      /* SIZE bytes of memory. */
    uint8_t *next;      /* Next unused byte of memory. */
    hash_t  *ht;        /* Hash table, maps filename to beginning of data. */
} cache_t;

#endif