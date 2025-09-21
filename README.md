# HTG Estimator

HTG Estimator is a Python-based command line tool that applies the HTG Pro Services estimating rules
for Orlando, Florida. It ingests structured client requests (JSON or YAML), applies internal labor
rates, local market labor benchmarks, material waste/drift buffers, and produces a client-ready
markdown estimate.

## Features

- Implements HTG internal labor rate of **$90/hour** with automated scope breakdown aggregation.
- Uses published Orlando market labor benchmarks for multiple trades with citations.
- Applies default **12% waste** and **5% price drift** to material line items.
- Automatically handles stage surcharges ($50 per additional mobilization).
- Generates a professional estimate formatted per HTG guidelines, including assumptions, exclusions,
  pricing tables, material itemization, totals, and clarifying questions.
- Supports attachments metadata so estimators can reference client photos/drawings.

## Installation

The project ships with a standard `pyproject.toml`. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the `htg-estimator` console script.

## Usage

Generate an estimate from a JSON or YAML request file:

```bash
htg-estimator estimate examples/sample_request.json
```

Write the output to a file and suppress console printing:

```bash
htg-estimator estimate examples/sample_request.json --output estimate.md --suppress-stdout
```

Create a starter template (JSON by default, YAML optional):

```bash
htg-estimator sample --format yaml > my_request.yaml
```

## Input Structure

Each request file must include:

- `client_name` – Client or prospect name.
- `project_address` – Job location (optional but recommended).
- `request_description` – One or two sentence summary of the prospect's ask.
- `services` – Array of services/scopes to price. Each service supports:
  - `name` – Friendly service label.
  - `service_type` – Used to map Orlando market labor data (see `htg_estimator/market_data.py`).
  - `breakdown` – List of labor phases (prep, demo, install, finish, cleanup, etc.) with low/high hours.
    If a quick allowance is needed you can pass `labor_hours` instead.
  - `materials` – Optional list of material line items with quantities, unit costs, and notes.
  - `assumptions` / `exclusions` – Additional notes appended to the defaults.
  - `stage_returns` – Number of additional mobilizations requiring a $50 surcharge each.
  - `permit_required` – Boolean flag to call out likely permitting.
- `attachments` – Optional list of `{path, kind, description}` objects for photos, drawings, or measurements.
- `site_conditions` – Optional bullets for access/constraints.
- `clarifying_questions` – Pre-seeded client questions that will be appended to the output.

## Example

A fully populated sample request is located at `examples/sample_request.json`. Run:

```bash
htg-estimator estimate examples/sample_request.json --output estimate.md
```

The generated `estimate.md` will contain the formatted estimate ready to share with the client.

## Testing

Install development dependencies and execute the unit tests with:

```bash
pip install -e .[development]
pytest
```

## License

This project is released under the MIT License.

