# Testing Protocol for pymodaq_plugins_pyrpl

This document outlines the procedures for running the comprehensive test suite for the `pymodaq_plugins_pyrpl` project.

## 1. Setup

All commands should be run from the root of the project.

### 1.1. Create a Virtual Environment

It is highly recommended to use a virtual environment to avoid conflicts with system-wide packages.

```bash
python3 -m venv venv_test
source venv_test/bin/activate
```

### 1.2. Install Dependencies

Install the plugin in editable mode with its main and test dependencies:

```bash
pip install -e .[test]
```

## 2. Running Tests

The test suite is divided into three categories: unit, integration, and end-to-end (hardware). You can run them individually or all at once.

### 2.1. Running All Tests (Excluding Hardware)

To run all unit and integration tests, execute the following command:

```bash
pytest
```

This will automatically discover and run all tests that are not marked as `hardware` tests.

### 2.2. Running Unit Tests Only

To run only the fast, isolated unit tests:

```bash
pytest tests/unit
```

### 2.3. Running Integration Tests Only

To run the integration tests that check the interaction between components:

```bash
pytest tests/integration
```

### 2.4. Running End-to-End Hardware Tests

**WARNING:** These tests require a real Red Pitaya device connected to the network at the IP address `100.107.106.75`.

To run the hardware tests, use the `-m` flag to select the `hardware` marker:

```bash
pytest -m hardware
```

## 3. Code Coverage

The test suite is configured to measure code coverage using `pytest-cov`. The goal is to maintain a coverage of at least 90%.

### 3.1. Generating a Coverage Report

To run all tests (excluding hardware) and generate a coverage report in the terminal, run:

```bash
pytest --cov=src/pymodaq_plugins_pyrpl
```

### 3.2. Generating an HTML Report

For a more detailed, interactive report, you can generate an HTML version:

```bash
pytest --cov=src/pymodaq_plugins_pyrpl --cov-report=html
```

After running this command, open the `htmlcov/index.html` file in your web browser.