# Publishing to PyPI

This guide shows how to publish `deepagent-dash` to PyPI using `uv`.

## Prerequisites

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Get PyPI API Token**:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with scope for this project
   - Save the token securely

## Build and Test Locally

### 1. Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 2. Build the Package

Using `uv`:
```bash
uv build
```

This creates:
- `dist/deepagent_dash-0.1.0-py3-none-any.whl` (wheel)
- `dist/deepagent-dash-0.1.0.tar.gz` (source distribution)

### 3. Test the Build Locally

Install in a virtual environment to test:
```bash
# Create test environment
uv venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from local build
uv pip install dist/deepagent_dash-0.1.0-py3-none-any.whl

# Test the CLI
deepagent-dash --help
deepagent-dash init test-project

# Test Python API
python -c "from deepagent_dash import run_app; print('Import successful')"

# Cleanup
deactivate
rm -rf test-env
```

## Publish to Test PyPI (Recommended First)

### 1. Install twine

```bash
uv pip install twine
```

### 2. Upload to Test PyPI

```bash
uv run twine upload --repository testpypi dist/*
```

Enter your TestPyPI credentials when prompted:
- Username: `__token__`
- Password: Your TestPyPI API token

### 3. Test Installation from Test PyPI

```bash
uv pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    deepagent-dash
```

Note: `--extra-index-url` allows installing dependencies from PyPI while getting your package from TestPyPI.

## Publish to PyPI (Production)

### 1. Upload to PyPI

```bash
uv run twine upload dist/*
```

Enter your PyPI credentials:
- Username: `__token__`
- Password: Your PyPI API token

### 2. Verify Installation

```bash
# In a fresh environment
uv pip install deepagent-dash

# Test it works
deepagent-dash --help
```

### 3. View on PyPI

Your package will be available at:
- https://pypi.org/project/deepagent-dash/

## Publishing Checklist

Before publishing, ensure:

- [ ] Version number updated in `pyproject.toml`
- [ ] Version number updated in `deepagent_dash/__init__.py`
- [ ] README.md is up to date
- [ ] LICENSE file is present
- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `black deepagent_dash/`
- [ ] No sensitive data in the package
- [ ] Git tag created: `git tag v0.1.0 && git push --tags`
- [ ] Built successfully: `uv build`
- [ ] Tested locally from wheel
- [ ] Published to TestPyPI first
- [ ] Tested installation from TestPyPI
- [ ] Ready for production PyPI

## Automated Publishing with GitHub Actions (Optional)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Build package
        run: uv build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          uv pip install twine
          uv run twine upload dist/*
```

Add your PyPI token to GitHub Secrets:
- Go to repository Settings → Secrets → Actions
- Add `PYPI_API_TOKEN` with your PyPI API token

## Version Bumping

For new releases:

1. Update version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Update version in `deepagent_dash/__init__.py`:
   ```python
   __version__ = "0.2.0"
   ```

3. Commit and tag:
   ```bash
   git add pyproject.toml deepagent_dash/__init__.py
   git commit -m "Bump version to 0.2.0"
   git tag v0.2.0
   git push && git push --tags
   ```

4. Rebuild and republish:
   ```bash
   rm -rf dist/
   uv build
   uv run twine upload dist/*
   ```

## Troubleshooting

### Build Errors

If `uv build` fails:
```bash
# Check pyproject.toml syntax
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"

# Verify package structure
ls -R deepagent_dash/
```

### Upload Errors

**Error: File already exists**
- You cannot re-upload the same version
- Bump the version number and rebuild

**Error: Invalid credentials**
- Verify you're using `__token__` as username
- Check your API token is correct and not expired

**Error: Package name conflict**
- Package name is already taken on PyPI
- Choose a different name in `pyproject.toml`

### Installation Issues

**Error: No matching distribution found**
- Wait a few minutes for PyPI to index
- Check package name spelling
- Verify version exists on PyPI

## Security Best Practices

1. **Never commit API tokens** - Use environment variables or GitHub Secrets
2. **Use scoped tokens** - Create project-specific tokens on PyPI
3. **Enable 2FA** on your PyPI account
4. **Revoke old tokens** after publishing
5. **Review package contents** before publishing:
   ```bash
   tar -tzf dist/deepagent-dash-0.1.0.tar.gz
   ```

## Resources

- [PyPI Documentation](https://packaging.python.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/tutorials/packaging-projects/)
