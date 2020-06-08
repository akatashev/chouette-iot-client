import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="chouette-client",
    version="0.1.0",
    author="Artem Katashev",
    author_email="aharr@rowanleaf.net",
    description="Python Client for Chouette-IoT metrics collection agent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/akatashev/chouette-iot-client",
    packages=setuptools.find_packages(),
    install_requires=["redis"],
    classifierds=[
        "Programming Language :: Python :: 3",
        "License:: OSI Approved:: Apache Software License",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6'
)