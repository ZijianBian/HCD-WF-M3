# Contributing to HCD Workflow

Thank you for your interest in contributing to the HCD Workflow project! This guide summarizes the key steps and expectations for contributors. 

## Code of Conduct

- Be respectful and professional.
- Provide constructive feedback.
- Help maintain code quality.
- Document your changes.

## Getting Started

1. Fork or clone the repository.
2. Create a feature branch.
3. Make your changes.
4. Test thoroughly.
5. Submit a pull request.

## Development Process

### Branching Strategy

- `main` – production releases.
- `develop` – active development branch.
- `feature/*` – new features.
- `bugfix/*` – bug fixes.
- `release/*` – release preparation.

### Creating a Feature Branch

```bash
git checkout develop
git pull
git checkout -b feature/my-feature-name
```

### Making Changes

1. Write clear, concise code.
2. Follow the existing code style.
3. Add docstrings to functions and classes.
4. Update relevant documentation.

## Code Style

We follow PEP 8 with a few project-specific rules:

- Line length: 120 characters.
- Use Black for formatting.
- Use flake8 for linting.
- Use pylint for code quality checks.

### Formatting Code

```bash
# Format all code
black --line-length 120 hcdworkflow/ gui/ tools/ workflow/

# Check style
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/

# Run pylint
pylint --max-line-length=120 hcdworkflow/
```

## Testing

Run the workflow against bundled test data:

```bash
# Test single slice
hcdslice_nogui -c tests/data/GRAYSCALE/

# Test full workflow
hcd_nogui -c tests/data/GRAYSCALE/

# Test GUI (if applicable)
hcd_gui
```

### Static Analysis

```bash
bash ci-sdcc/st05-staticanalysis.sh
```

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**

- `feat`: new feature  
- `fix`: bug fix  
- `docs`: documentation changes  
- `style`: formatting changes  
- `refactor`: refactoring  
- `test`: adding/updating tests  
- `chore`: maintenance tasks  

**Example:**

```
feat: Add support for new ECRH actor

- Integrate TORBEAM actor
- Add configuration template
- Update documentation

Closes #123
```

## Pull Request Process

1. Update documentation for new features.
2. Ensure all tests pass.
3. Update the changelog if applicable.
4. Request review from maintainers.
5. Address review comments promptly.

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Tested with test data
- [ ] Manual testing performed
- [ ] Static analysis passed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Commits are properly formatted
```

## Documentation

### Updating Documentation

Documentation lives in `docs/source/`.

```bash
# Edit .rst files
vim docs/source/user/usage.rst

# Build documentation
cd docs
make html

# View locally
xdg-open build/html/index.html
```

### Documentation Style

- Use reStructuredText (`.rst`).
- Include concise code examples.
- Add cross-references where relevant.
- Keep prose clear and focused.

---

By following these guidelines, you help keep HCD Workflow stable and maintainable. Thanks again for contributing!