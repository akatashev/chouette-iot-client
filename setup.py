import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="chouette-iot-client",
    version="0.0.1",
    author="Artem Katashev",
    author_email="aharr@rowanleaf.net",
    description="Python Client for Chouette-IoT metrics collection agent",
    license="Apache License, Version 2.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/akatashev/chouette-iot-client",
    packages=setuptools.find_packages(),
    install_requires=["redis"],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Monitoring"
    ],
    python_requires='>=3.6'
)
