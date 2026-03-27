# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

## Types of Contributions

### Report Bugs

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

You can never have enough documentation! Please feel free to contribute to any
part of the documentation, such as the official docs, docstrings, or even
on the web in blog posts, articles, and such.

### Submit Feedback

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get Started!

Ready to contribute? Here's how to set up `pyreel` for local development.

1. Fork the repo on GitHub and clone your fork locally.

2. Install [uv](https://docs.astral.sh/uv/):

    ```console
    $ pip install uv
    ```

3. Install `pyreel` with dev dependencies:

    ```console
    $ uv sync --extra dev
    ```

4. Install system dependencies (FFmpeg and ImageMagick):

    ```console
    # macOS
    $ brew install ffmpeg imagemagick

    # Ubuntu/Debian
    $ sudo apt install ffmpeg imagemagick
    ```

5. Use `git` to create a branch for local development and make your changes:

    ```console
    $ git checkout -b name-of-your-bugfix-or-feature
    ```

6. When you're done making changes, run the tests:

    ```console
    $ uv run pytest tests/ -v
    ```

7. Commit your changes and open a pull request.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include additional tests if appropriate.
2. All external API calls must be mocked in tests — no real network calls.
3. If the pull request adds functionality, the docs should be updated.
4. The pull request should work for all currently supported operating systems and Python >= 3.11.

## Code of Conduct

Please note that the `pyreel` project is released with a
Code of Conduct. By contributing to this project you agree to abide by its terms.
