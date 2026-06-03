from flask import Flask, render_template_string, jsonify
from monitor.api_checker import check_api
from monitor.config import APIS
from collections import defaultdict
from datetime import datetime
import random

app = Flask(__name__)

history = defaultdict(list)
status_count = defaultdict(lambda: {"up": 0, "total": 0})
last_state = {}
alert_log = []

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>API Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {
            margin: 0;
            font-family: Arial;
            background: #0b1220;
            color: #e5e7eb;
        }

        h1 {
            text-align: center;
            padding: 15px;
            color: #60a5fa;
        }

        .container {
            display: flex;
            gap: 20px;
            padding: 20px;
        }

        .main { flex: 3; }
        .side { flex: 1; }

        #summary {
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 15px;
            text-align: center;
            color: #93c5fd;
            font-weight: bold;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            overflow: hidden;
        }

        th, td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #1f2937;
        }

        th {
            background: #111827;
            color: #93c5fd;
        }

        .badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        .HEALTHY { background: #16a34a; color: white; }
        .DOWN { background: #dc2626; color: white; }
        .DEGRADED { background: #facc15; color: black; }

        canvas {
            margin-top: 20px;
            background: rgba(255,255,255,0.03);
            padding: 10px;
            border-radius: 10px;
        }

        .alertBox {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            border-radius: 10px;
            height: 500px;
            overflow-y: auto;
        }

        .alertItem {
            padding: 8px;
            margin-bottom: 8px;
            border-left: 3px solid #60a5fa;
            font-size: 13px;
            background: rgba(255,255,255,0.03);
            border-radius: 5px;
        }

        .containerBox {
            display: flex;
        }
    </style>
</head>

<body>

<h1>API Monitoring System</h1>

<div id="summary">Loading...</div>

<div class="container">

    <div class="main">

        <table>
            <thead>
                <tr>
                    <th>API</th>
                    <th>Status</th>
                    <th>Response</th>
                    <th>Uptime</th>
                </tr>
            </thead>
            <tbody id="table-body"></tbody>
        </table>

        <canvas id="chart"></canvas>

    </div>

    <div class="side">
        <h3 style="text-align:center;color:#93c5fd;">Alert History</h3>
        <div class="alertBox" id="alerts">No alerts yet</div>
    </div>

</div>

<script>
let chart;

async function fetchData() {
    const res = await fetch("/data");
    const data = await res.json();

    const results = data.results;
    const summary = data.summary;
    const alerts = data.alerts;

    document.getElementById("summary").innerHTML =
        "🟢 Healthy: " + summary.healthy +
        " | 🟡 Degraded: " + summary.degraded +
        " | 🔴 Down: " + summary.down;

    let alertHTML = "";
    alerts.slice(-6).forEach(a => {
        alertHTML += `<div class="alertItem">${a}</div>`;
    });
    document.getElementById("alerts").innerHTML = alertHTML || "No alerts yet";

    let rows = "";

    const labels = results[0].history.map((_, i) => i + 1);
    const datasets = [];

    results.forEach(api => {

        rows += `
        <tr>
            <td>${api.url}</td>
            <td><span class="badge ${api.health}">${api.health}</span></td>
            <td>${api.response_time}s</td>
            <td>${api.uptime}%</td>
        </tr>
        `;

        datasets.push({
            label: api.url,
            data: api.history,
            borderColor: getColor(api.url),
            fill: false,
            tension: 0.3
        });
    });

    document.getElementById("table-body").innerHTML = rows;

    if (!chart) {
        const ctx = document.getElementById("chart").getContext("2d");

        chart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: datasets
            }
        });
    } else {
        chart.data.labels = labels;
        chart.data.datasets = datasets;
        chart.update();
    }
}

function getColor(url) {
    if (url.includes("posts")) return "#38bdf8";
    if (url.includes("users")) return "#22c55e";
    return "#facc15";
}

fetchData();
setInterval(fetchData, 5000);
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/data")
def data():
    results = []
    healthy = 0
    down = 0
    degraded = 0

    for api in APIS:
        result = check_api(api)
        url = result["url"]
        status = result["health"]

        base = result["response_time"]
        noise = random.uniform(0.1, 0.6)

        if status == "DOWN":
            result["response_time"] = 3 + random.uniform(1, 3)
        else:
            result["response_time"] = round(base + noise, 3)

        history[url].append(result["response_time"])
        if len(history[url]) > 10:
            history[url].pop(0)

        status_count[url]["total"] += 1
        if status == "HEALTHY":
            status_count[url]["up"] += 1
            healthy += 1
        elif status == "DOWN":
            down += 1
        else:
            degraded += 1

        uptime = round((status_count[url]["up"] / status_count[url]["total"]) * 100, 2)

        prev = last_state.get(url)

        if prev != status:
            from monitor.alerts import send_sms
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if status == "DOWN":
                msg = f"ALERT [{time}]: {url} DOWN"
                send_sms(msg)
                alert_log.append(msg)

            elif status == "HEALTHY" and prev == "DOWN":
                msg = f"RECOVERY [{time}]: {url} BACK ONLINE"
                send_sms(msg)
                alert_log.append(msg)

        last_state[url] = status

        result["history"] = history[url]
        result["uptime"] = uptime

        results.append(result)

    return jsonify({
        "results": results,
        "summary": {
            "healthy": healthy,
            "down": down,
            "degraded": degraded
        },
        "alerts": alert_log
    })

if __name__ == "__main__":
    app.run(debug=True)