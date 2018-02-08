#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pypbap",
    version="1.0.0",
    description="Bluetooth - PhoneBook Access Profile",
    author="Kannan.Subramani@bmw.de",
    license="Proprietary",
    classifiers=[
        "Development Status :: 5 - In progress/Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="pbap",
    zip_safe=False,
    packages=find_packages(),
    dependency_links=["https://bitbucket.org/dboddie/pyobex/get/tip.zip#egg=pyobex-0.26"],
    install_requires=[
        "pybluez",
        "pyobex>=0.26",
        "pymongo"
    ],
)
