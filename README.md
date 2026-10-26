# Modular Specification and Online Evaluation of Temporal Logic Formulae

**Authors**: Simone Silvetti, Michele Loreti, Laura Nenzi

A Python framework for specifying temporal logic formulae in a modular way and evaluating them online (i.e., incrementally over incoming data streams). The library provides elementary building blocks (elements, nodes, functions) and notifiers for hooking into event conditions, along with example use cases.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [What's new in 1.1.0](#whats-new-in-110)
- [Installation](#installation)
- [Repository Structure](#repository-structure)
- [Use Cases / Examples](#use-cases--examples)
- [Testing](#testing)
- [Contact](#contact)

---

## Overview

This project provides a purely Python-based framework for:
- **Modular specification** of temporal logic formulae in terms of atomic elements, operators, and composition.
- **Online (incremental) evaluation** of such formulae against input streams of symbolic states.
- **Notifiers** to trigger callbacks or actions when specified temporal conditions become true (or false).
- **Example use cases** (e.g., weather monitoring and continuous glucose monitoring) illustrating how to apply the framework to real-time data streams.

---

## Features

- **Elementary building blocks**: define predicates, signals, or atomic conditions as Python callables or expressions.
- **Temporal operators**: combine elements with temporal constructs.
- **Online evaluation engine**: processes incoming symbolic states one at a time, updating formula evaluation in constant or optimal time.
- **Notifiers / Callbacks**: register handlers that fire when a formula is satisfied and/or violated.
- **Modular design**: easy to extend with new predicate types, operators, or custom notifiers.
- **Test suite**: unit tests for core modules to ensure correctness.
- **Example use cases**: demonstrations (`usecase/weather` and `usecase/cgm`) showing how to integrate with data sources and drive the evaluation engine.

---

## What's new in 1.1.0

Bug fixes in the binary and n-ary nodes, in the input nodes and in the window minimum/maximum (now exact, with
Lemire's monotonic queue), faster arithmetic, removal of broken or unused operators, and end-to-end regression tests.
See [CHANGELOG.md](CHANGELOG.md).

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
.
├── gemon/
│   ├── elements.py      # intervals (symbolic states), interval operators, sliding windows
│   ├── functions.py     # polynomials of degree <= 2 and the undefined function
│   ├── nodes.py         # nodes of the monitoring graph: input, unary, binary, n-ary, window nodes
│   └── notifiers.py     # observer pattern used by the nodes
├── tests/
│   ├── test_elements.py, test_nodes.py   # unit tests
│   ├── test_bugfixes.py                  # regression tests of the fixed bugs
│   └── test_e2e.py                       # end-to-end semantics against tests/golden/
├── examples/RV2025/     # the case studies of the RV 2025 paper
│   ├── weather/         # weather monitoring
│   └── cgm/             # continuous glucose monitoring
├── docs/                # extended version of the RV 2025 paper
├── pyproject.toml
└── requirements.txt
```
---
## Use Cases / Examples

Under `examples/RV2025/`, example scripts demonstrate application of the framework. Please refer to `examples/RV2025/weather` or `examples/RV2025/cgm`.

### Weather Events
![Weather events](examples/RV2025/weather/fig/gif_weather.gif)

### Artificial Pancreas
![Artificial pancreas](examples/RV2025/cgm/fig/gif_cgm.gif)
---

## Testing

- **tests/test_elements.py**, **tests/test_nodes.py**: unit tests of the core modules.
- **tests/test_bugfixes.py**: regression tests of the bugs fixed in 1.1.0.
- **tests/test_e2e.py**: end-to-end tests of the semantics. Every node of the RV 2025 case studies and of synthetic
  scenarios (random, irregularly sampled signals through every kind of node) must produce exactly the signal stored
  in `tests/golden/e2e.json`. Regenerate it (`python tests/make_golden.py`) only for an intended change of the
  semantics.

Run tests with:
```bash
python -m pytest tests
```
Ensure your virtual environment is active and dependencies installed.

---

## Contact

For questions or feedback, contact the authors:
- Simone Silvetti (University of Trieste)
- Michele Loreti (University of Camerino)
- Laura Nenzi (University of Trieste)
