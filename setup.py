from setuptools import setup, find_packages

setup(
    name="pytest-vts",
    version="0.1.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["pytest", "responses"],
    entry_points={
        "pytest11": [
            "pytest_vts = pytest_vts"
        ],
    },

    # metadata for upload to PyPI
    author="Bogdan Hodorog",
    author_email="bogdan.hodorog@gmail.com",
    description="pytest plugin for automatic recording of http stubbed tests",
    license="MIT",
    keywords="pytest plugin http stub mock record",
)
