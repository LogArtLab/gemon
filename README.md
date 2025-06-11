# Modular Specification and Online Evaluation of Temporal Logic Formulae

**Authors**: Simone Silvetti, Michele Loreti, Laura Nenzi

A Python framework for specifying temporal logic formulae in a modular way and evaluating them online (i.e., incrementally over incoming data streams). The library provides elementary building blocks (elements, nodes, functions) and notifiers for hooking into event conditions, along with example use cases.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Repository Structure](#repository-structure)
- [Use Cases / Examples](#use-cases--examples)
- [Testing](#testing)
- [Contact](#contact)

---

## Overview

This project provides a purely Python-based framework for:
- **Modular specification** of temporal logic formulae (e.g., LTL or similar) in terms of atomic elements, operators, and composition.
- **Online (incremental) evaluation** of such formulae against input streams of symbolic states or events.
- **Notifiers** to trigger callbacks or actions when specified temporal conditions become true (or false).
- **Example use cases** (e.g., weather monitoring) illustrating how to apply the framework to real-time data streams or simulations.

---

## Features

- **Elementary building blocks**: define predicates, signals, or atomic conditions as Python callables or expressions.
- **Temporal operators**: combine elements with temporal constructs (e.g., eventually, always, until).
- **Online evaluation engine**: processes incoming symbolic states one at a time, updating formula evaluation in constant or optimal time.
- **Notifiers / Callbacks**: register handlers that fire when a formula is satisfied and/or violated.
- **Modular design**: easy to extend with new predicate types, operators, or custom notifiers.
- **Test suite**: unit tests for core modules to ensure correctness.
- **Example use cases**: demonstrations (e.g., in `usecase/weather`) showing how to integrate with data sources and drive the evaluation engine.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/LogArtLab/gemon.git
   cd gemon
   ```
2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Ensure you have at least the versions specified in `requirements.txt`.

---

## Repository Structure

```
gemon/
│
├── elements.py          # Definitions of atomic elements/predicates or base building blocks
├── functions.py         # Utility functions or higher-order helpers for combining or manipulating elements/nodes
├── nodes.py             # Definitions of temporal operators, AST nodes, and evaluation logic
├── notifiers.py         # Classes or utilities for registering callbacks/actions on formula evaluation events
├── requirements.txt     # Python dependencies
│
├── test_elements.py     # Unit tests for elements module
├── test_nodes.py       # Unit tests for nodes (operators, evaluation engine, etc.)
│
└── usecase/             # Example use cases or demo scripts showing how to apply the framework
    └── weather/         # Example related to weather monitoring
    └── cgm/             # Example related to CGM monitoring
```

## Use Cases / Examples

Under `usecase/`, example scripts demonstrate application of the framework.

### Weather Use Case (`usecase/weather`)
Likely workflow:
1. **Data source**: fetch or simulate weather data (temperature, humidity, etc.).
2. **Atomic predicates**: e.g., “temperature above threshold”, “humidity below limit”.
3. **Temporal formulae**: e.g., “if temperature stays above X for Y time units then trigger alert”.
4. **Notifiers**: register callbacks to log or alert when conditions are met.
5. **Online loop**: periodically fetch data and feed to the evaluation engine.
6. **Results**: save logs, plots, or send notifications.
To run the example:
```bash
cd usecase/weather
python weather.py
```
Modify parameters or configuration within `weather.py` as needed.

---

## Testing

Unit tests are provided for core modules:
- **test_elements.py**: tests for atomic predicate behavior and utilities.
- **test_nodes.py**: tests for temporal operators and evaluator correctness.

Run tests with:
```bash
pytest
```
Ensure your virtual environment is active and dependencies installed.

---

## Contact

For questions or feedback, contact the authors:
- Simone Silvetti
- Michele Loreti
- Laura Nenzi
