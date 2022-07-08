from setuptools import setup, find_packages

setup(
    name="testme",
    version="0.0.1",
    license="AGPLv3+",
    classifiers=[],
    install_requires=[
        "flask~=1.1",
        "flask-sqlalchemy~=2.4",
        "flask-babel~=2.0",
        "flask-markdown~=0.3",
        "flask-wtf~=0.14",
        "markupsafe~=2.0,<2.1",
        "environ-config~=20.1",
    ],
    packages=find_packages(),
)
