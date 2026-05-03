from setuptools import setup, find_packages

with open("README.rst", "r") as fh:
	long_description = fh.read()

setup(name="moku_util", version=1.0, 
    package_dir={"": "lib"},
    packages=find_packages(), 
    author="Charles Blakemore", 
    author_email="chas.blakemore@gmail.com",
    description="Basic utilities for Moku:Go",
    long_description=long_description,
    url="https://github.com/charlesblakemore/moku_util",
	)