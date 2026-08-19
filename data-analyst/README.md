# Data Analyst Agent Template

An AI agent that queries databases, generates visual charts, and writes structured analysis reports.

## Features

- **Multi-Database Support** — Connects to PostgreSQL, MySQL, or SQLite based on environment configuration.
- **Safe SQL Execution** — Validates all queries as read-only (SELECT/WITH only). Blocks DROP, DELETE, TRUNCATE, ALTER, and other destructive operations.
- **Chart Generation** — Creates bar, line, pie, and scatter charts from query results. Saves as PNG with configurable DPI and styling.
- **Statistical Analysis** — Computes mean, median, standard deviation, quartiles, IQR, range, min/max for numeric columns.
- **Anomaly Detection** — Uses the IQR (Interquartile Range) method to identify outliers in datasets.
- **Report Generation** — Writes structured markdown reports with findings, statistics, visualizations, data quality notes, and recommendations.

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | Required in production |
| `DB_TYPE` | Database type: `sqlite`, `postgresql`, `mysql` | `sqlite` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name (or file path for SQLite) | `:memory:` |
| `DB_USER` | Database user | (empty) |
| `DB_PASSWORD` | Database password | (empty) |
| `CHART_OUTPUT_DIR` | Directory for generated charts | `/tmp/agntspark-charts` |

### LLM Settings

- **Provider:** OpenAI
- **Model:** gpt-4o
- **Temperature:** 0.2 (very low, for precise analytical output)
- **Max Tokens:** 8192

## Usage

### Run in Test Mode

```bash
pip install -r requirements.txt
python agent.py
```

Creates a temporary SQLite database with sample sales data and runs through all agent capabilities: SQL execution, statistical summary, anomaly detection, chart generation, and report writing.

### Deploy with AgntSpark

```bash
agntspark deploy --template ./data-analyst
```

### Programmatic Usage

```python
from agent import DataAnalystAgent

agent = DataAnalystAgent()
result = agent.execute_sql("SELECT product, SUM(revenue) FROM sales GROUP BY product")
chart = agent.generate_chart(
    {"x": [r[0] for r in result["rows"]], "y": [r[1] for r in result["rows"]]},
    {"chart_type": "bar", "title": "Revenue by Product"}
)
```

## Tools

| Tool | Description |
|---|---|
| `execute_sql` | Execute validated read-only SQL queries |
| `generate_chart` | Generate bar/line/pie/scatter charts from data |
| `statistical_summary` | Compute statistical summary of numeric data |
| `detect_anomalies` | Detect outliers using IQR method |
| `write_report` | Write structured markdown analysis report |
| `analyze` | Full pipeline: query → stats → chart → report |

## SQL Safety

The agent validates all queries before execution:
- Only `SELECT` and `WITH` (CTE) statements are allowed
- `DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `GRANT`, `REVOKE`, `SHUTDOWN` are blocked
- Maximum 10,000 rows returned per query
- 30-second query timeout
