from setuptools import setup, find_packages

setup(
    name="blockwart",
    version="0.4.0-dev",
    description="config management for Python addicts",
    author="Torsten Rehn",
    author_email="torsten@rehn.tel",
    license="GPLv3",
    url="http://blockwart.org",
    package_dir={'': "src"},
    packages=find_packages("src"),
    entry_points={
        'console_scripts': [
            "bw=blockwart.cmdline:main",
        ],
    },
    keywords=["configuration", "config", "management"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
    install_requires=[
        "distribute",
        "Fabric >= 0.9.4",
        "Mako",
    ],
    zip_safe=False,
)
