from setuptools import setup

setup(
    name='fuzzyhttp',
    version='0.1.0',
    description='Fuzzy matching HTTP file server with autocomplete and fallback',
    author='PakCyberbot',
    author_email='pakcyberbot@gmail.com',
    packages=['fuzzyhttp'],
    entry_points={
        'console_scripts': [
            'fuzzyhttp = fuzzyhttp.server:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.6',
)
