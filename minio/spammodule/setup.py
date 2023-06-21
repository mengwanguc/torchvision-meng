from distutils.core import setup, Extension

minio_module = Extension('minio', sources = ['miniomodule.c'])

setup(name = 'MinIO',
      version = '1.0',
      description = 'Python MinIO file cache module.',
      author = 'Gus Waldspurger',
      author_email = 'gus@waldspurger.com',
      ext_modules = [
            Extension(minio_module)
      ])