from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize("cpyfim.pyx",compiler_directives={"language_level": "3"},annotate=True  )
)