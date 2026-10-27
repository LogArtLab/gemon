#!/usr/bin/env python3
"""
Regenerate tests/golden/e2e.json, the reference end-to-end traces.

Only run this when a change of the monitoring semantics is intended. The current
golden file was generated from commit 7456d15 (branch main), then regenerated on
branch iot when MinWindowNode/MaxWindowNode started ignoring undefined values: only
min_window_3 and max_window_3 of synthetic_windows_undefined_* changed.

    python tests/make_golden.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e2e_trace  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "e2e.json")

if __name__ == "__main__":
    traces = e2e_trace.all_traces()
    with open(GOLDEN, "w") as f:
        json.dump(traces, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"{len(traces)} scenarios written to {GOLDEN}")
