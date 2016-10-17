from sys import version_info

from setuptools import find_packages, setup


dependencies = [
    "cryptography",
    "Jinja2",
    "Mako",
    "passlib",
    "requests >= 1.0.0",
]
if version_info < (3, 2, 0):
    dependencies.append("futures")

setup(
    name="bundlewrap",
    version="2.9.0",
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
    test_suite="tests",
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
    install_requires=dependencies,
    extras_require={  # used for wheels
        ':python_version=="2.7"': ["futures"],
    },
    zip_safe=False,
)
