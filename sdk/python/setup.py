from setuptools import setup, find_packages

setup(
    name="ticos-client",
    version="0.1.8",
    author="Ticos Team",
    author_email="admin@tiwater.com",
    description="A client SDK for communicating with Ticos Server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tiwater/ticos-client",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
