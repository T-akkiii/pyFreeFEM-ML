#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from setuptools import setup, find_packages, Command
from setuptools.command.install import install

class BuildPluginCommand(Command):
    """Custom command to build the FreeFEM plugin."""
    description = 'Build the FreeFEM plugin'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugins')
        subprocess.check_call(['make', '-C', plugin_dir])
        print("FreeFEM plugin built successfully.")

class InstallPluginCommand(Command):
    """Custom command to install the FreeFEM plugin."""
    description = 'Install the FreeFEM plugin to FreeFEM plugin directory'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugins')
        try:
            # Try to determine FreeFEM plugin directory
            freefem_plugin_dir = os.path.expanduser("~/.ff++/lib/")
            if not os.path.exists(freefem_plugin_dir):
                os.makedirs(freefem_plugin_dir)
            
            subprocess.check_call(['make', 'install', '-C', plugin_dir])
            print(f"FreeFEM plugin installed to {freefem_plugin_dir}")
        except Exception as e:
            print(f"Warning: Failed to install FreeFEM plugin: {e}")
            print("You may need to manually install the plugin using 'make install' in the plugins directory.")

class CustomInstallCommand(install):
    """Custom install command that builds and installs the FreeFEM plugin."""
    def run(self):
        self.run_command('build_plugin')
        self.run_command('install_plugin')
        install.run(self)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyfreefem_ml",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python-FreeFEM interface with shared memory communication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pyfreefem-ml",
    packages=['pyfreefem_ml'],  # Explicitly specify the package
    package_dir={'pyfreefem_ml': 'pyfreefem_ml'},  # Specify package directory
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.20.0",
        # その他の依存関係を追加
    ],
    entry_points={
        "console_scripts": [
            "pyfreefem=pyfreefem_ml.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        'pyfreefem_ml': ['plugins/scripts/**/*.edp'],
    },
    cmdclass={
        'build_plugin': BuildPluginCommand,
        'install_plugin': InstallPluginCommand,
        'install': CustomInstallCommand,
    },
) 