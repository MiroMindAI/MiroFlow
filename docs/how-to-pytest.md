# Overview

general pattern:
- AVOID `if __name__ == __main__: main()` in library/package code. Instead, 
- WRITE `def test_xxx()` in `tests/test_xxx.py`.

```python
# test code with `uv run src/foo.py`
# in src/foo.py
def main():
    pass

if __name__ == "__main__":
    main()

# test code with `uv run pytest -q -s tests/test_foo.py::test_foo_func`
# or test code with VSCode
# in tests/test_foo.py
def test_foo_func():
    pass

def test_foo_func_2():
    pass
```

# Use Pytest in VSCode

- Toggle `Testing` in side panel.
- Choose `pytest` over `unittest`.
- Choose `/tests` as discovery folder.
- If successful, should see something like this:

![](./figures/pytest-success-setup.png)

# How to ...

## write a simple test and test it?

- file name must either be `test_*.py` or `*_test.py`.
- function name must be `def test_*()`.
- left click the green button in VSCode:

![](./figures/run-pytest-from-vscode.png)

## write a simple test and step through it?

- add breakpoints in VSCode.
- right click the green button and choose `Debug Test`:

![](./figures/debug-test-from-vscode.png)

## show logs from failed test?

```shell
# no option required
uv run pytest
# default
uv run pytest -rfE
```
- For more options, see [detailed summary](https://docs.pytest.org/en/stable/how-to/output.html#producing-a-detailed-summary-report)

## show logs from passed tests?

```shell
# only test that passed
uv run pytest -rpP
```

- For more options, see [detailed summary](https://docs.pytest.org/en/stable/how-to/output.html#producing-a-detailed-summary-report)

## show logs from all tests?

```shell
# only test that passed
uv run pytest -rA
```

- For more options, see [detailed summary](https://docs.pytest.org/en/stable/how-to/output.html#producing-a-detailed-summary-report)

## check what tests will be run?

```shell
# list all tests
uv run pytest --collect-only
# list all tests with their fixture
uv run pytest --collect-only --fixtures-per-test
```

## select tests by file names?

```shell
# ignore files
uv run pytest --ignore=tests/foo/test_bar.py tests/
# ignore folders
uv run pytest --ignore=tests/hello/ tests/
# selected file
uv run pytest tests/foo/test_bar.py
# selected folder
uv run pytest tests/hello/
```

## select tests by function names?

```shell
# all test functions and classes 
# whose name contains 'test_method' or 'test_other'
uv run pytest -k 'test_method or test_other' tests/
# all test functions and classes
# marked with `foo` and not `bar`.
uv run pytest -m 'foo and not bar` tests/
```