#!/usr/bin/env python3
"""
Router Watchdog - Web UI

Simple dashboard to view logs and trigger actions.
"""

import subprocess
import sys
from flask import Flask, jsonify, render_template_string

from config import load_config

config = load_config()

app = Flask(__name__)

LOG_FILE = config["log_file"]
CRON_LOG = "/var/log/cron.log"

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Router Watchdog</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
  h1 { color: #00d4ff; margin-bottom: 20px; }
  .actions { margin-bottom: 20px; display: flex; gap: 10px; }
  button {
    padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;
    font-family: monospace; font-size: 14px; font-weight: bold;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-seed { background: #e94560; color: white; }
  .btn-reset { background: #0f3460; color: white; }
  .btn-refresh { background: #533483; color: white; }
  .status { margin-bottom: 20px; padding: 10px; border-radius: 4px; display: none; }
  .status.success { display: block; background: #1b4332; color: #95d5b2; }
  .status.error { display: block; background: #462124; color: #f4978e; }
  .status.running { display: block; background: #1b3a4b; color: #89c2d9; }
  .logs { display: flex; gap: 20px; }
  .log-panel { flex: 1; }
  .log-panel h2 { color: #00d4ff; margin-bottom: 8px; font-size: 14px; }
  pre {
    background: #0f0f23; padding: 12px; border-radius: 4px; overflow: auto;
    max-height: 70vh; font-size: 12px; line-height: 1.5; white-space: pre-wrap;
    word-wrap: break-word;
  }
</style>
</head>
<body>
  <h1>Router Watchdog</h1>
  <div class="actions">
    <button class="btn-seed" onclick="run('seed')">Initialize Rule</button>
    <button class="btn-reset" onclick="run('reset')">Reset Timer</button>
    <button class="btn-refresh" onclick="refreshLogs()">Refresh Logs</button>
  </div>
  <div id="status" class="status"></div>
  <div class="logs">
    <div class="log-panel">
      <h2>Monitor Log</h2>
      <pre id="monitor-log">Loading...</pre>
    </div>
    <div class="log-panel">
      <h2>Cron Log</h2>
      <pre id="cron-log">Loading...</pre>
    </div>
  </div>
<script>
  function setStatus(msg, cls) {
    const el = document.getElementById('status');
    el.textContent = msg;
    el.className = 'status ' + cls;
  }

  async function run(action) {
    const btns = document.querySelectorAll('button');
    btns.forEach(b => b.disabled = true);
    setStatus('Running...', 'running');
    try {
      const res = await fetch('/api/' + action, { method: 'POST' });
      const data = await res.json();
      setStatus(data.message, data.success ? 'success' : 'error');
      refreshLogs();
    } catch (e) {
      setStatus('Request failed: ' + e, 'error');
    }
    btns.forEach(b => b.disabled = false);
  }

  async function refreshLogs() {
    try {
      const res = await fetch('/api/logs');
      const data = await res.json();
      document.getElementById('monitor-log').textContent = data.monitor || '(empty)';
      document.getElementById('cron-log').textContent = data.cron || '(empty)';
    } catch (e) {
      console.error(e);
    }
    return Promise.resolve();
  }

  function scrollToBottom() {
    document.querySelectorAll('pre').forEach(el => el.scrollTop = el.scrollHeight);
  }

  refreshLogs().then(scrollToBottom);
  setInterval(() => refreshLogs().then(scrollToBottom), 30000);
</script>
</body>
</html>
"""


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/logs")
def logs():
    def read_log(path, tail=200):
        try:
            with open(path) as f:
                lines = f.readlines()
                return "".join(lines[-tail:])
        except FileNotFoundError:
            return ""

    return jsonify(monitor=read_log(LOG_FILE), cron=read_log(CRON_LOG))


@app.route("/api/seed", methods=["POST"])
def seed():
    result = subprocess.run(
        [sys.executable, "/app/seed_rule.py"],
        capture_output=True, text=True, timeout=30,
    )
    return jsonify(
        success=result.returncode == 0,
        message=result.stdout.strip() or result.stderr.strip(),
    )


@app.route("/api/reset", methods=["POST"])
def reset():
    result = subprocess.run(
        [sys.executable, "/app/reset_timer.py"],
        capture_output=True, text=True, timeout=30,
    )
    return jsonify(
        success=result.returncode == 0,
        message=result.stdout.strip() or result.stderr.strip(),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
