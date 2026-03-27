# Building Python Packages

We are following the guide from [Python Packages](https://py-pkgs.org/welcome) by Tomas Beuzen and Tiffany Timbers for the structure of this template repo.  This readme documents differences from their guide and elements that need to be changed in the repo once you use this template for your own named package.

## Files to change once template is copied

These files/folders largely need to be edited to use the name of your package instead of the `pypackage_template` name. The `pyproject.toml` will also need author editing.

- [`tests/test_template_package.py`](https://github.com/byuirpytooling/pypackage_template/blob/main/tests/test_template_package.py)
- [`src/pypackage_template`](https://github.com/byuirpytooling/pypackage_template/tree/main/src/pypackage_template)
- [`src/pypackage_template/__init__.py`](https://github.com/byuirpytooling/pypackage_template/blob/main/src/pypackage_template/__init__.py)
- [`main/pyproject.toml`](https://github.com/byuirpytooling/pypackage_template/blob/main/pyproject.toml)
- [`mkdocs.yml`](https://github.com/byuirpytooling/pypackage_template/blob/main/mkdocs.yml)
- [`docs/API.md`](https://github.com/byuirpytooling/pypackage_template/blob/main/docs/API.md)

## Differences from the Python Packages book

###  Python Installation

We will use [uv](https://docs.astral.sh/uv/guides/install-python/) instead of [conda](https://anaconda.org/anaconda/conda).

### Installing uv and python

1. Follow [uv's installation scripts](https://docs.astral.sh/uv/getting-started/installation/#installation-methods)
2. Now run `uv python install --default`.
  - You can see your available python versions with `uv python list`.
  - If you want a specific version of python you can run `uv python install 3.12` for example.
  - You can upgrade to the latest supported patch release for each version with `uv python upgrade`
3. Now you can install the two python packages recommended `uv pip install poetry cookiecutter --system`
4. I propose skipping the PyPI setup and the rest of chapter 2 for now.

## mkdocs-material

1. mkdocs-material with `uv pip install mkdocs-material --system`
2. [Guide on mkdocs-material](https://www.youtube.com/watch?v=xlABhbnNrfI) and his [companion website for this video](https://jameswillett.dev/getting-started-with-material-for-mkdocs/)
 - However, we are using `uv` and will use `uv run mkdocs new .` instead of `mkdocs new .`

## Handy `uv` commands 

### Install a package from Github repository

```bash
uv pip install "git+https://github.com/byuirpytooling/pypackage_template.git@main"
```

### Installing the package in development into the Python environment 

The `--editable` allows us to create an installation that points back to your project directory instead of copying the code into site-packages. With this, we can now edit the source files, and the installed package in the environment is automatically updated.

```bash
uv sync --editable
```

The above option replaces examples where you would run.

```bash
uv pip install -e .
```

## Directory structure

```bash
pypackage_template
├── .readthedocs.yml           ┐
├── CHANGELOG.md               │
├── CONDUCT.md                 │
├── CONTRIBUTING.md            │
├── docs                       │
│   ├── changelog.md           │
│   ├── conduct.md             │
│   ├── conf.py                │ 
│   ├── contributing.md        │ Package documentation
│   ├── example.ipynb          │
│   ├── index.md               │
│   ├── make.bat               │
│   ├── Makefile               │
│   └── requirements.txt       │
├── LICENSE                    │
├── README.md                  ┘
├── pyproject.toml             ┐ 
├── src                        │
│   └── pypackage_template     │ Package source code, metadata,
│       ├── __init__.py        │ and build instructions 
│       └── pycounts.py        ┘
└── tests                      ┐
    └── test_pycounts.py       ┘ Package tests
```
