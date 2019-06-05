from setuptools import setup, find_packages

exec(open("./src/pytest_vts/version.py").read())

with open("PyPI_LONGDESC.rst") as fd:
    long_description = fd.read()

keywords = ("pytest plugin http stub mock record responses recorder "
            "vcr betamax automatic")

setup(
    name="pytest-vts",
    version=__version__,  # noqa
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["pytest >=2.3", "responses", "cookies", "six"],
    entry_points={
        "pytest11": [
            "pytest_vts = pytest_vts"
        ],
    },

    # metadata for upload to PyPI
    author="Bogdan Hodorog",
    author_email="bogdan.hodorog@gmail.com",
    description="pytest plugin for automatic recording of http stubbed tests",
    long_description=long_description,
    license="MIT",
    keywords=keywords,
    classifiers=["Framework :: Pytest"],
    project_urls={
        'Bug Reports': 'https://github.com/bhodorog/pytest-vts/issues',
        'Source': 'https://github.com/bhodorog/pytest-vts',
    },
)
