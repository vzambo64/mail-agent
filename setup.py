#!/usr/bin/env python3
"""
Mail-Agent Setup Script

For development installation:
    pip install -e .

For production, use the Debian package instead.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mail-agent",
    version="1.0.0",
    author="Viktor Zambo",
    author_email="mail-agent@zamboviktor.hu",
    description="AI-powered automatic email reply agent for Postfix",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vzambo64/mail-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Email",
        "Topic :: Communications :: Email :: Mail Transport Agents",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mail-agent=main:main",
        ],
    },
    data_files=[
        ("share/man/man1", ["man/mail-agent.1"]),
    ],
    include_package_data=True,
)

