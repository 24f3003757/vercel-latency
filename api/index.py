from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# CORS middleware — allows any browser/dashboard to POST to this endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # accept requests from any domain
    allow_methods=["POST"],   # only POST is needed per the spec
    allow_headers=["*"],
)

# The telemetry data is embedded directly in the code.
# Why? Because Vercel serverless functions can't read from the filesystem
# at runtime — there's no guarantee your data file will be available.
# Embedding it as a Python list is the safe, portable approach.
TELEMETRY = [
  {"region":"apac","service":"recommendations","latency_ms":136.31,"uptime_pct":97.112,"timestamp":20250301},
  {"region":"apac","service":"analytics","latency_ms":229.51,"uptime_pct":98.582,"timestamp":20250302},
  {"region":"apac","service":"support","latency_ms":168.83,"uptime_pct":97.562,"timestamp":20250303},
  {"region":"apac","service":"catalog","latency_ms":224.07,"uptime_pct":98.117,"timestamp":20250304},
  {"region":"apac","service":"support","latency_ms":159.28,"uptime_pct":98.633,"timestamp":20250305},
  {"region":"apac","service":"payments","latency_ms":167.82,"uptime_pct":97.991,"timestamp":20250306},
  {"region":"apac","service":"payments","latency_ms":129.46,"uptime_pct":98.011,"timestamp":20250307},
  {"region":"apac","service":"analytics","latency_ms":183.47,"uptime_pct":97.777,"timestamp":20250308},
  {"region":"apac","service":"payments","latency_ms":106.96,"uptime_pct":99.256,"timestamp":20250309},
  {"region":"apac","service":"analytics","latency_ms":193.43,"uptime_pct":97.301,"timestamp":20250310},
  {"region":"apac","service":"support","latency_ms":210.53,"uptime_pct":97.741,"timestamp":20250311},
  {"region":"apac","service":"recommendations","latency_ms":124.97,"uptime_pct":99.123,"timestamp":20250312},
  {"region":"emea","service":"catalog","latency_ms":150.26,"uptime_pct":97.234,"timestamp":20250301},
  {"region":"emea","service":"catalog","latency_ms":174.2,"uptime_pct":99.295,"timestamp":20250302},
  {"region":"emea","service":"payments","latency_ms":227.88,"uptime_pct":99.454,"timestamp":20250303},
  {"region":"emea","service":"payments","latency_ms":168.73,"uptime_pct":97.957,"timestamp":20250304},
  {"region":"emea","service":"checkout","latency_ms":168.35,"uptime_pct":97.451,"timestamp":20250305},
  {"region":"emea","service":"catalog","latency_ms":211.57,"uptime_pct":98.089,"timestamp":20250306},
  {"region":"emea","service":"payments","latency_ms":169.84,"uptime_pct":98.264,"timestamp":20250307},
  {"region":"emea","service":"payments","latency_ms":215.37,"uptime_pct":97.628,"timestamp":20250308},
  {"region":"emea","service":"analytics","latency_ms":213.29,"uptime_pct":98.537,"timestamp":20250309},
  {"region":"emea","service":"recommendations","latency_ms":133.9,"uptime_pct":97.859,"timestamp":20250310},
  {"region":"emea","service":"support","latency_ms":118.48,"uptime_pct":99.462,"timestamp":20250311},
  {"region":"emea","service":"payments","latency_ms":131.25,"uptime_pct":99.235,"timestamp":20250312},
  {"region":"amer","service":"support","latency_ms":202.61,"uptime_pct":99.256,"timestamp":20250301},
  {"region":"amer","service":"support","latency_ms":219.66,"uptime_pct":98.846,"timestamp":20250302},
  {"region":"amer","service":"recommendations","latency_ms":194.6,"uptime_pct":98.434,"timestamp":20250303},
  {"region":"amer","service":"support","latency_ms":201.15,"uptime_pct":99.49,"timestamp":20250304},
  {"region":"amer","service":"catalog","latency_ms":207.73,"uptime_pct":97.715,"timestamp":20250305},
  {"region":"amer","service":"payments","latency_ms":170.28,"uptime_pct":98.379,"timestamp":20250306},
  {"region":"amer","service":"payments","latency_ms":165.24,"uptime_pct":97.939,"timestamp":20250307},
  {"region":"amer","service":"catalog","latency_ms":139.08,"uptime_pct":97.961,"timestamp":20250308},
  {"region":"amer","service":"support","latency_ms":227.14,"uptime_pct":99.476,"timestamp":20250309},
  {"region":"amer","service":"checkout","latency_ms":171.57,"uptime_pct":98.34,"timestamp":20250310},
  {"region":"amer","service":"support","latency_ms":138.87,"uptime_pct":98.122,"timestamp":20250311},
  {"region":"amer","service":"recommendations","latency_ms":194.63,"uptime_pct":99.279,"timestamp":20250312},
]


# Pydantic model: defines the shape of the incoming JSON body.
# FastAPI uses this to automatically parse and validate the request.
class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


def compute_p95(values: list) -> float:
    """
    95th percentile using linear interpolation.

    Why not just sort and grab index 0.95*n?
    Because with small datasets, that lands between two values.
    Linear interpolation gives the same result as numpy's default percentile.

    Example with 12 values (indices 0–11):
      rank = 0.95 * (12 - 1) = 10.45
      lower = 10, upper = 11
      result = values[10] + 0.45 * (values[11] - values[10])
    """
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    rank = 0.95 * (n - 1)
    lower = int(rank)
    upper = lower + 1
    if upper >= n:
        return sorted_vals[-1]
    frac = rank - lower
    return sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower])


@app.post("/api/latency")
def latency_stats(request: LatencyRequest):
    result = {}

    for region in request.regions:
        # Filter records for this region
        records = [r for r in TELEMETRY if r["region"] == region]

        if not records:
            result[region] = {"error": "no data found"}
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes   = [r["uptime_pct"]  for r in records]

        result[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 4),
            "p95_latency": round(compute_p95(latencies), 4),
            "avg_uptime":  round(sum(uptimes)   / len(uptimes),   4),
            # breach = latency strictly greater than threshold
            "breaches":    sum(1 for l in latencies if l > request.threshold_ms),
        }

    return result
