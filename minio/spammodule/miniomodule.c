#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "../minio/minio.h"


/* Python wrapper for cache_t type. */
typedef struct {
    PyObject_HEAD
    cache_t cache;
} PyCache;

/* PyCache deallocate method. */
static void
PyCache_dealloc(PyCache *self)
{
    /* Free the memory allocate for the cache region. */
    if (self->cache.data != NULL) {
        free(self->cache.data);
    }

    /* Free the cache struct itself. */
    Py_TYPE(self)->tp_free((PyObject *) self);
}

/* PyCache creation method. */
static PyObject *
PyCache_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    /* Allocate the PyCache struct. */
    PyCache *self;
    if ((self = (PyCache *) type->tp_alloc(type, 0)) == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    return (PyObject *) self;
}

/* PyCache initialization method. */
static int
PyCache_init(PyCache *self, PyObject *args, PyObject *kwds)
{
    /* Parse arguments. */
    size_t size;
    static char *kwlist[] = {"size", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|i", kwlist, &size)) {
        PyErr_BadArgument();
        return -1;
    }
    
    /* Initialize the cache. */
    cache_init(&self->cache.data, size, POLICY_MINIO);

    return 0;
}

/* PyCache read/get method. */
static PyObject *
PyCache_read(PyCache *self, PyObject *args, PyObject *kwds)
{
    /* Parse arguments. */
    char filepath[MAX_PATH_LENGTH + 1];
    static char *kwlist[] = {"filepath", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|s", kwlist, &filepath)) {
        PyErr_BadArgument();
        return NULL;
    }

    return NULL;
}

/* PyCache methods. */
static PyMethodDef PyCache_methods[] = {
    {"get", (PyCFunction) PyCache_read, METH_KEYWORDS, "Get a file through the cache."},
    {NULL} /* Sentinel. */
};

static PyTypeObject PythonCacheType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "minio.PythonCache",
    .tp_doc = PyDoc_STR("MinIO Python cache"),
    .tp_basicsize = sizeof(PyCache),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,

    /* Methods. */
    .tp_dealloc = PyCache_dealloc,
    .tp_new = PyCache_new,
    .tp_init = PyCache_init,
    .tp_methods = PyCache_methods,
};


static PyMethodDef CacheMethods[] = {
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef miniomodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "minio",
    .m_doc = "Python module to implement a MinIO file cache.",
    .m_size = -1,
    .m_methods = CacheMethods,
};

PyMODINIT_FUNC
PyInit_miniomodule(void)
{
    PyObject *module;
    
    /* Check PythonCacheType is ready. */
    if (PyType_Ready(&PythonCacheType) < 0) {
        return NULL;
    }

    /* Create Python module. */
    if ((module = PyModule_Create(&miniomodule)) == NULL) {
        return NULL;
    }

    /* Add the PythonCacheType type. */
    Py_INCREF(&PythonCacheType);
    if (PyModule_AddObject(module, "Cache", (PyObject *) &PythonCacheType) < 0) {
        Py_DECREF(&PythonCacheType);
        Py_DECREF(module);
        return NULL;
    }

    return module;
}