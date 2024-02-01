import pathlib

from setuptools import find_packages
from setuptools import setup


def find_required():
    with open("requirements.txt") as f:
        return f.read().splitlines()


HERE = pathlib.Path(__file__).parent
README = open("README.md").read()
setup(
    name="maxwelld",
    version="0.0.17",
    description="docker compose testing env orchestrator",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Yuriy Sagitov",
    author_email="pro100.ko10ok@gmail.com",
    python_requires=">=3.10.0",
    url="https://github.com/ko10ok/maxwelld",
    license="Apache-2.0",
    packages=find_packages(exclude=("tests",)),
    install_requires=find_required(),
    entry_points={},
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
