# Contributing to Team Diamonds 

This document outlines the process for contributing to this open source library.

---
## Getting Started / Setup

### Prerequisites

- [Python >= 3.11]
- [uv](https://docs.astral.sh/uv/) — used to manage the virtual environment and dependencies

### Fork & Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/shubham739/team-diamonds.git
cd team-diamonds
```

### Install Dependencies

```bash
# Create the virtual environment and install all dependencies
uv sync
```

### Running Locally

```bash
# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Project Structure Overview

```
team-diamonds/
├── components/		# Source files
├── tests/			# Test suite
└── docs/			# Documentation
```

---

## Pull Request Process

### Branch Naming

Use descriptive branch names following the pattern:

```
[netid]-[hw#]-[feature_name]

```

Examples: `tct297-hw1-implementation_update`

### Workflow

1. Create a branch from `main` (or the designated development branch).
2. Following the test driven development method, write tests to cover your changes first
2. Then make your changes, and only commit atomic and reasonable changes
4. Run the full test suite locally and confirm it passes.
5. Update relevant documentation if behavior or APIs have changed.
6. Open a pull request against `main` and fill out the PR template.

### PR Template and Checklist

## Description of Changes
<!-- What does this PR do? Why is it needed? 1 or 2 sentences is okay. -->


---

## Tests

<!-- If applicable, describe the tests written for this change. Per the TDD policy, tests must be written before new code. -->


---

## Checklist

- [ ] Tests were written before code (TDD)
- [ ] All tests pass (`uv run pytest`)
- [ ] No unrelated changes are included
- [ ] Documentation updated if behavior or APIs changed
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas


### Review Process

- A reviewer will review your PR upon request
- Address review feedback by pushing additional commits
- Once approved, the reviewer will merge your PR

### Commit Message Convention

Ensure your commit is short but descriptive. 

#### Examples:
handle empty string input in [method-name]
add [feature name] to impl component

---

## Testing Guidelines

### Running Tests

```bash
# Run the full test suite
uv run pytest

# Run a specific test file
uv run pytest tests/[test_file.py]
```

### Test Coverage

```bash
# Generate a coverage report
[pending instructions]
```

Aim to maintain **[85%]** or greater test coverage. PRs that significantly reduce coverage will be asked to add additional tests before merging.

### Writing Tests

This project follows test driven development: a test must be written before any new code is written. The typical cycle is:

1. Write a failing test that defines the expected behavior.
2. Write the minimum code necessary to make the test pass.
3. Refactor as needed, keeping the tests green.

Additional conventions:

- Place integration and end-to-end tests in the `tests/` directory of the root folder. 
- Place unit tests in the component's `tests/` 
- Name test files `test_[module_name].py` to follow pytest conventions.