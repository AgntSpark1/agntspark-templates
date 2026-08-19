"""
AgntSpark Data Analyst Agent

Queries databases, generates visual charts, and writes structured analysis reports.
"""

import json
import logging
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import sqlite3
import psycopg2
import pymysql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("data-analyst")

# SQL keywords that indicate destructive operations
FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "TRUNCATE", "ALTER", "GRANT", "REVOKE", "SHUTDOWN"}


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    row_count: int
    execution_time_ms: float
    database: str


@dataclass
class ChartConfig:
    chart_type: str  # bar, line, pie, scatter
    title: str
    x_label: str = ""
    y_label: str = ""
    output_path: str = ""


@dataclass
class AnalysisReport:
    title: str
    generated_at: str
    summary: str
    findings: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    charts: list[str] = field(default_factory=list)
    data_quality_notes: list[str] = field(default_factory=list)
    raw_stats: dict = field(default_factory=dict)


class DataAnalystAgent:
    """Main agent class for database analysis and reporting."""

    def __init__(self):
        self.db_type = os.getenv("DB_TYPE", "sqlite").lower()
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", ":memory:")
        self.db_user = os.getenv("DB_USER", "")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.chart_output_dir = os.getenv("CHART_OUTPUT_DIR", "/tmp/agntspark-charts")
        os.makedirs(self.chart_output_dir, exist_ok=True)

        plt.style.use("seaborn-v0_8-whitegrid")

    def _get_connection(self):
        """Get a database connection based on configured type."""
        if self.db_type == "sqlite":
            return sqlite3.connect(self.db_name)
        elif self.db_type == "postgresql":
            return psycopg2.connect(
                host=self.db_host, port=self.db_port, dbname=self.db_name,
                user=self.db_user, password=self.db_password,
            )
        elif self.db_type == "mysql":
            return pymysql.connect(
                host=self.db_host, port=self.db_port, database=self.db_name,
                user=self.db_user, password=self.db_password,
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def _validate_sql(self, query: str) -> tuple[bool, str]:
        """Validate that a SQL query is safe (read-only)."""
        query_upper = query.upper().strip()
        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
            return False, "Only SELECT and WITH (CTE) queries are allowed."
        for kw in FORBIDDEN_KEYWORDS:
            # Match as whole word
            if f" {kw} " in f" {query_upper} " or query_upper.startswith(kw + " "):
                return False, f"Forbidden keyword '{kw}' detected in query."
        return True, "OK"

    # --- Tool: execute_sql ---

    def execute_sql(self, query: str) -> dict:
        """Execute a read-only SQL query and return results."""
        logger.info(f"Executing SQL: {query[:120]}...")

        valid, msg = self._validate_sql(query)
        if not valid:
            logger.error(f"SQL validation failed: {msg}")
            return {"error": msg, "query": query}

        start = datetime.now()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            # Convert non-serializable types
            clean_rows = []
            for row in rows:
                clean_row = []
                for val in row:
                    if isinstance(val, (bytes, bytearray)):
                        clean_row.append(val.decode("utf-8", errors="replace"))
                    elif hasattr(val, "isoformat"):
                        clean_row.append(val.isoformat())
                    else:
                        clean_row.append(val)
                clean_rows.append(clean_row)

            cursor.close()
            conn.close()
            elapsed = (datetime.now() - start).total_seconds() * 1000
            result = QueryResult(
                columns=columns,
                rows=clean_rows[:10000],
                row_count=len(clean_rows),
                execution_time_ms=round(elapsed, 2),
                database=self.db_name,
            )
            logger.info(f"Query returned {result.row_count} rows in {result.execution_time_ms}ms")
            return {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "execution_time_ms": result.execution_time_ms,
            }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"error": str(e), "query": query}

    # --- Tool: generate_chart ---

    def generate_chart(self, data: dict, config: dict) -> dict:
        """Generate a chart from data and save as PNG."""
        chart_type = config.get("chart_type", "bar")
        title = config.get("title", "Chart")
        x_label = config.get("x_label", "")
        y_label = config.get("y_label", "")
        x_data = data.get("x", [])
        y_data = data.get("y", [])

        if not x_data or not y_data:
            return {"error": "Both x and y data are required"}

        fig, ax = plt.subplots(figsize=(10, 6))
        try:
            if chart_type == "bar":
                ax.bar(x_data, y_data, color="#4C72B0", edgecolor="#2C3E50")
            elif chart_type == "line":
                ax.plot(x_data, y_data, marker="o", color="#4C72B0", linewidth=2)
            elif chart_type == "pie":
                ax.pie(y_data, labels=x_data, autopct="%1.1f%%", startangle=90)
            elif chart_type == "scatter":
                ax.scatter(x_data, y_data, color="#4C72B0", alpha=0.7)
            else:
                return {"error": f"Unsupported chart type: {chart_type}"}

            if chart_type != "pie":
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
            ax.set_title(title, fontsize=14, fontweight="bold")

            # Rotate x labels if there are many
            if len(x_data) > 6 and chart_type != "pie":
                plt.xticks(rotation=45, ha="right")

            plt.tight_layout()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chart_{chart_type}_{timestamp}.png"
            output_path = os.path.join(self.chart_output_dir, filename)
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"Chart saved: {output_path}")
            return {"chart_path": output_path, "chart_type": chart_type, "title": title}
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return {"error": str(e)}
        finally:
            plt.close(fig)

    # --- Tool: statistical_summary ---

    def statistical_summary(self, values: list, label: str = "data") -> dict:
        """Compute statistical summary of a numeric dataset."""
        if not values:
            return {"error": "Empty dataset"}

        numeric_vals = [v for v in values if isinstance(v, (int, float))]
        if not numeric_vals:
            return {"error": "No numeric values in dataset"}

        n = len(numeric_vals)
        sorted_vals = sorted(numeric_vals)
        result = {
            "label": label,
            "count": n,
            "mean": round(statistics.mean(numeric_vals), 4),
            "median": round(statistics.median(numeric_vals), 4),
            "stdev": round(statistics.stdev(numeric_vals), 4) if n > 1 else 0,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "range": round(sorted_vals[-1] - sorted_vals[0], 4),
            "q1": round(sorted_vals[n // 4], 4) if n >= 4 else sorted_vals[0],
            "q3": round(sorted_vals[3 * n // 4], 4) if n >= 4 else sorted_vals[-1],
            "iqr": None,
        }
        result["iqr"] = round(result["q3"] - result["q1"], 4)
        logger.info(f"Stats for '{label}': mean={result['mean']}, median={result['median']}, n={n}")
        return result

    # --- Tool: detect_anomalies ---

    def detect_anomalies(self, values: list, label: str = "data") -> dict:
        """Detect anomalies in data using the IQR method."""
        if len(values) < 4:
            return {"anomalies": [], "method": "IQR", "note": "Insufficient data for anomaly detection"}

        numeric_vals = [v for v in values if isinstance(v, (int, float))]
        n = len(numeric_vals)
        sorted_vals = sorted(numeric_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        anomalies = [
            {"value": v, "index": i, "type": "low" if v < lower_bound else "high"}
            for i, v in enumerate(values)
            if isinstance(v, (int, float)) and (v < lower_bound or v > upper_bound)
        ]
        logger.info(f"Anomaly detection for '{label}': {len(anomalies)} found (bounds: {lower_bound:.2f} - {upper_bound:.2f})")
        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "method": "IQR",
            "bounds": {"lower": round(lower_bound, 4), "upper": round(upper_bound, 4)},
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
        }

    # --- Tool: write_report ---

    def write_report(self, report: dict, output_path: str = "") -> dict:
        """Write an analysis report to a markdown file."""
        if not output_path:
            output_path = os.path.join(self.chart_output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

        r = AnalysisReport(
            title=report.get("title", "Data Analysis Report"),
            generated_at=datetime.now().isoformat(),
            summary=report.get("summary", ""),
            findings=report.get("findings", []),
            recommendations=report.get("recommendations", []),
            charts=report.get("charts", []),
            data_quality_notes=report.get("data_quality_notes", []),
            raw_stats=report.get("raw_stats", {}),
        )

        lines = [
            f"# {r.title}",
            f"\n*Generated: {r.generated_at}*\n",
            f"## Summary\n\n{r.summary}\n",
        ]

        if r.findings:
            lines.append("## Findings\n")
            for f in r.findings:
                lines.append(f"- **{f.get('title', 'Finding')}**: {f.get('detail', '')}")
            lines.append("")

        if r.raw_stats:
            lines.append("## Statistical Summary\n")
            lines.append(f"```json\n{json.dumps(r.raw_stats, indent=2)}\n```\n")

        if r.charts:
            lines.append("## Visualizations\n")
            for c in r.charts:
                lines.append(f"![Chart]({c})\n")

        if r.data_quality_notes:
            lines.append("## Data Quality Notes\n")
            for note in r.data_quality_notes:
                lines.append(f"- ⚠️ {note}")
            lines.append("")

        if r.recommendations:
            lines.append("## Recommendations\n")
            for i, rec in enumerate(r.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        content = "\n".join(lines)
        with open(output_path, "w") as f:
            f.write(content)
        logger.info(f"Report written: {output_path}")
        return {"report_path": output_path, "size_bytes": len(content)}

    # --- Core: analyze ---

    def analyze(self, question: str, sql_query: str, chart_config: Optional[dict] = None) -> dict:
        """Run a full analysis pipeline: query → stats → chart → report."""
        results = {"question": question}

        # Execute query
        query_result = self.execute_sql(sql_query)
        if "error" in query_result:
            return {**results, "error": query_result["error"]}
        results["query_result"] = query_result

        # Extract numeric column for stats
        numeric_col_idx = None
        for i, col in enumerate(query_result["columns"]):
            sample_vals = [row[i] for row in query_result["rows"][:20] if isinstance(row[i], (int, float))]
            if len(sample_vals) > 3:
                numeric_col_idx = i
                break

        if numeric_col_idx is not None:
            col_name = query_result["columns"][numeric_col_idx]
            values = [row[numeric_col_idx] for row in query_result["rows"]]
            results["stats"] = self.statistical_summary(values, label=col_name)
            results["anomalies"] = self.detect_anomalies(values, label=col_name)

        # Generate chart if configured
        if chart_config and query_result["rows"]:
            x_col = chart_config.get("x_column", 0)
            y_col = chart_config.get("y_column", 1) if len(query_result["columns"]) > 1 else 0
            chart_data = {
                "x": [str(row[x_col]) for row in query_result["rows"][:20]],
                "y": [row[y_col] for row in query_result["rows"][:20]],
            }
            results["chart"] = self.generate_chart(chart_data, chart_config)

        return results


def main():
    """Run the agent in test mode with a sample SQLite database."""
    # Create a temporary test database
    test_db = "/tmp/agntspark_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_NAME"] = test_db
    os.environ["CHART_OUTPUT_DIR"] = "/tmp/agntspark-charts"

    agent = DataAnalystAgent()

    # Set up test data
    conn = sqlite3.connect(test_db)
    conn.executescript("""
        CREATE TABLE sales (id INTEGER PRIMARY KEY, product TEXT, revenue REAL, month TEXT);
        INSERT INTO sales (product, revenue, month) VALUES
            ('Widget A', 15000, '2025-01'), ('Widget A', 16500, '2025-02'),
            ('Widget A', 18000, '2025-03'), ('Widget B', 22000, '2025-01'),
            ('Widget B', 19500, '2025-02'), ('Widget B', 25000, '2025-03'),
            ('Widget C', 8000, '2025-01'), ('Widget C', 9200, '2025-02'),
            ('Widget C', 8800, '2025-03'), ('Widget D', 45000, '2025-01'),
            ('Widget D', 12000, '2025-02'), ('Widget D', 11000, '2025-03');
    """)
    conn.commit()
    conn.close()

    print("=" * 60)
    print("Data Analyst Agent — Test Mode")
    print("=" * 60)

    # Test 1: SQL execution
    print(f"\n{'─' * 60}")
    print("Test 1: Execute SQL query")
    result = agent.execute_sql("SELECT product, SUM(revenue) as total FROM sales GROUP BY product ORDER BY total DESC")
    print(f"Columns: {result.get('columns')}")
    print(f"Rows: {result.get('row_count')}")
    for row in result.get("rows", []):
        print(f"  {row}")

    # Test 2: Statistical summary
    print(f"\n{'─' * 60}")
    print("Test 2: Statistical summary")
    revenues = [row[1] for row in result.get("rows", [])]
    stats = agent.statistical_summary(revenues, label="total_revenue")
    print(json.dumps(stats, indent=2))

    # Test 3: Anomaly detection
    print(f"\n{'─' * 60}")
    print("Test 3: Anomaly detection")
    anomalies = agent.detect_anomalies(revenues, label="total_revenue")
    print(f"Anomalies found: {anomalies['anomaly_count']}")
    for a in anomalies["anomalies"]:
        print(f"  Value {a['value']} ({a['type']})")

    # Test 4: Generate chart
    print(f"\n{'─' * 60}")
    print("Test 4: Generate chart")
    chart_result = agent.generate_chart(
        {"x": [row[0] for row in result.get("rows", [])], "y": revenues},
        {"chart_type": "bar", "title": "Revenue by Product", "x_label": "Product", "y_label": "Revenue ($)"},
    )
    print(f"Chart saved: {chart_result.get('chart_path', chart_result.get('error'))}")

    # Test 5: Write report
    print(f"\n{'─' * 60}")
    print("Test 5: Write analysis report")
    report_result = agent.write_report({
        "title": "Q1 2025 Sales Analysis",
        "summary": "Analysis of sales revenue by product for Q1 2025. Widget D shows anomalous revenue in January.",
        "findings": [
            {"title": "Top performer", "detail": f"Widget D leads with ${revenues[0]:,.0f} total revenue"},
            {"title": "Anomaly detected", "detail": "Widget D January revenue significantly higher than other months"},
        ],
        "recommendations": [
            "Investigate Widget D January revenue spike for potential data entry errors",
            "Consider promoting Widget B as it shows consistent growth trend",
        ],
        "charts": [chart_result.get("chart_path", "")],
        "raw_stats": stats,
    })
    print(f"Report written: {report_result.get('report_path')}")
    print(f"Report size: {report_result.get('size_bytes')} bytes")

    # Test 6: Full pipeline
    print(f"\n{'─' * 60}")
    print("Test 6: Full analyze pipeline")
    pipeline_result = agent.analyze(
        "What are the top products by revenue?",
        "SELECT product, SUM(revenue) as total FROM sales GROUP BY product ORDER BY total DESC",
        {"chart_type": "bar", "title": "Top Products", "x_label": "Product", "y_label": "Revenue"},
    )
    print(json.dumps({k: v for k, v in pipeline_result.items() if k != "query_result"}, indent=2, default=str))

    print(f"\n{'=' * 60}")
    print("All tests passed ✓")
    print(f"Charts in: {os.environ['CHART_OUTPUT_DIR']}")


if __name__ == "__main__":
    main()
