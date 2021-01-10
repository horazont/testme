from setuptools import setup, find_packages

setup(
    name="testme",
    version="0.0.1",
    license="AGPLv3+",
    classifiers=[],
    install_requires=[
        "flask~=1.1",
        "flask-sqlalchemy~=2.4",
    ],
    packages=find_packages(),
)
