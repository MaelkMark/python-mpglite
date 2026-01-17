# Testing MPGLite

This guide describes how to test MPGLite. The tests are located in the [tests](tests) folder and are run using [pytest](https://docs.pytest.org/).

<!-- omit from toc -->
## Table of Contents
- [Requirements](#requirements)
- [Tests](#tests)
- [Running the tests](#running-the-tests)
- [Troubleshooting](#troubleshooting)
- [Automatic testing with GitHub Actions](#automatic-testing-with-github-actions)


## Requirements

To be able to run the tests, you need to have the [pytest](https://docs.pytest.org/) and mpglite installed.

Install pytest

```
pip install pytest
```

Install MPGLite as editable by running this command in the root of the repository:

```
pip install -e .
```

## Tests
The [tests](tests) folder includes the following files:
- [conftest.py](tests/conftest.py) — defines the fixtures for the tests
- [testingutils.py](tests/testingutils.py) — defines some utility functions for the tests
- The test files:
  - [test_connection.py](tests/test_connection.py) — tests the connection between the server and a client
  - [test_client.py](tests/test_client.py) — tests the functions of [client.py](src/mpglite/client.py) 
  - [test_communication.py](tests/test_communication.py) — tests the communication between the server and the clients
  - [test_game.py](tests/test_game.py) — tests the game functionalities and callbacks
  - [test_server.py](tests/test_server.py) — tests the functions of [utils.py](src/mpglite/utils.py)

These test files can be run independently, but individual test functions within a file cannot. Some tests require a preceding test to be run first. Therefore, run entire test files instead of individual test functions.


## Running the tests
If you want to run all the tests, simply run this command in the root of the repository:
```
pytest tests
```

To run a specific test file, simply this command in the root of the repository:
```
pytest tests/test_file_name.py
```

## Troubleshooting
Terminating the tests may not end all processes using the port. This could cause some or even all of the tests to fail. In this case, run [free_port.py](tests/free_port.py) (located in the tests folder). It kills port 8765 by default, but you can pass the port number as an argument (8888, for example).
```
python tests/free_port.py 8888
```

## Automatic testing with GitHub Actions
When a commit is pushed or a new pull request is opened, the tests are run automatically with GitHub Actions on all major Python versions from 3.10 to 3.14, in an Ubuntu environment. You can view the results of the tests on the [Actions](https://github.com/MaelkMark/python-mpglite/actions/workflows/tests.yml) page of the repository. The result of the latest tests is also shown on a badge in the [README](README.md).