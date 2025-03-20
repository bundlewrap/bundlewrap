from setuptools import find_packages, setup


setup(
    name="bundlewrap",
    version="4.22.0",
    description="Config management with Python",
    long_description=(
        "By allowing for easy and low-overhead config management, BundleWrap fills the gap between complex deployments using Chef or Puppet and old school system administration over SSH.\n"
        "While most other config management systems rely on a client-server architecture, BundleWrap works off a repository cloned to your local machine. It then automates the process of SSHing into your servers and making sure everything is configured the way it's supposed to be. You won't have to install anything on managed servers."
    ),
    author="Torsten Rehn",
    author_email="torsten@rehn.email",
    license="GPLv3",
    url="http://bundlewrap.org",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            "bw=bundlewrap.cmdline:main",
        ],
    },
    keywords=["configuration", "config", "management"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",  # remove hack in files.py import when EOL
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
    install_requires=[
        "cryptography",
        "Jinja2",
        "librouteros >= 3.0.0",
        "Mako",
        "passlib",
        "pyyaml",
        "requests >= 1.0.0",
        "rtoml ; python_version<'3.11'",
        "setuptools",
        "tomlkit",
    ],
    zip_safe=False,
)
