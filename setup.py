from setuptools import setup, find_packages

setup(
    name="taco-cli",
    version="0.1.0",
    description="Tool And Context Orchestrator - A CLI for Ollama LLMs with tool support",
    author="TACO Contributors",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/taco",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "ollama",
        "chromadb",
        "pydantic",
        "rich",
        "typer",
        "prompt_toolkit",
    ],
    entry_points={
        "console_scripts": [
            "taco=taco.cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
