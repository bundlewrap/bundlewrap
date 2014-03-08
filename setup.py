from setuptools import setup, find_packages

setup(
    name="blockwart",
    version="0.10.0",
    description="config management for Python addicts",
    long_description=(
        "By allowing for easy and low-overhead config management, Blockwart fills the gap between complex deployments using Chef or Puppet and old school system administration over SSH.\n"
        "While practically all other config management systems rely on a client-server architecture, Blockwart works off a repository cloned to your local machine. It then automates the process of SSHing into your servers and making sure everything is configured the way it's supposed to be. You won't have to install anything on managed servers."
    ),
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
        "Development Status :: 4 - Beta",
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
        "passlib",
    ],
    zip_safe=False,
)
