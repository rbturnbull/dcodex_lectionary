from setuptools import setup

requirements = [
    'Django>3',
    'django-polymorphic',
    'numpy',
    'pandas>=1.0.5',
    'matplotlib',
]

setup(
    install_requires=requirements,
)


