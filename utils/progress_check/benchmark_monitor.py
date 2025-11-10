"""
Benchmark Monitor with Web Interface

This script provides monitoring capabilities for any benchmark including:
- Real-time web dashboard
- Historical data tracking
- Progress monitoring

Usage:
    uv run utils/progress_check/benchmark_monitor.py [LOG_FOLDER_PATH] [OPTIONS]

Options:
    --web-port PORT       Web interface port (default: 8080)
"""

import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import os
import socket
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from omegaconf import OmegaConf


class WebDashboard:
    """Simple web dashboard for monitoring"""

    def __init__(self, monitor, port: int = 8080):
        self.monitor = monitor
        self.port = port
        self.server = None
        self.benchmark_name = monitor.benchmark_name

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return True
            except OSError:
                return False

    def _find_available_port(self, start_port: int, max_attempts: int = 100) -> int:
        """Find an available port starting from start_port"""
        port = start_port
        for _ in range(max_attempts):
            if self._is_port_available(port):
                return port
            port += 1
        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

    def start_server(self):
        """Start the web server with automatic port conflict resolution"""
        handler = self.create_handler()
        
        # Find an available port, starting from the requested port
        actual_port = self._find_available_port(self.port)
        
        # Update self.port to reflect the actual port being used
        if actual_port != self.port:
            print(f"Port {self.port} is already in use, using port {actual_port} instead")
            self.port = actual_port
        
        self.server = HTTPServer(("localhost", self.port), handler)
        print(f"Web dashboard available at: http://localhost:{self.port}")

        def run_server():
            self.server.serve_forever()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    def create_handler(self):
        """Create HTTP request handler"""
        monitor = self.monitor

        class DashboardHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                """Override to suppress HTTP request logs"""
                pass
            
            def do_GET(self):
                if self.path == "/":
                    self.send_dashboard()
                elif self.path == "/api/status":
                    self.send_json(monitor.get_status_json())
                elif self.path == "/api/tasks":
                    self.send_json(monitor.get_tasks_json())
                elif self.path.startswith("/api/task-report/"):
                    task_id = self.path.split("/")[-1]
                    self.send_task_report(task_id)
                else:
                    self.send_error(404)

            def send_dashboard(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                html = self.generate_dashboard_html()
                self.wfile.write(html.encode())

            def send_json(self, data):
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data, default=str).encode())

            def send_task_report(self, task_id):
                """Send task report for a specific task"""
                try:
                    # Try to find the task in the current running tasks
                    task_info = monitor.get_task_info(task_id)
                    if not task_info:
                        self.send_error(404, "Task not found")
                        return

                    # Generate report using the standalone report generator
                    report_content = monitor.generate_task_report(task_id)
                    if not report_content:
                        self.send_error(500, "Failed to generate report")
                        return

                    self.send_response(200)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(report_content.encode("utf-8"))

                except Exception as e:
                    self.send_error(500, f"Error generating report: {str(e)}")

            def generate_dashboard_html(self):
                benchmark_name = monitor.benchmark_name
                return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{benchmark_name} Monitor Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1976d2; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); transition: width 0.3s; }}
        .status-running {{ color: #ff9800; }}
        .status-completed {{ color: #4caf50; }}
        .status-failed {{ color: #f44336; }}
        .task-list {{ max-height: 400px; overflow-y: auto; }}
        .task-item {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .refresh-btn {{ background: #2196f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #1976d2; }}
        .view-report-btn {{ background: #4caf50; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 10px; font-size: 12px; }}
        .view-report-btn:hover {{ background: #45a049; }}
    </style>
    <script>
        function refreshData() {{
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    updateDashboard(data);
                    // Pass benchmark_type to updateTaskList
                    fetch('/api/tasks')
                        .then(response => response.json())
                        .then(tasks => updateTaskList(tasks, data.benchmark_type));
                }});
        }}
        
        function updateDashboard(data) {{
            document.getElementById('progress-pct').textContent = data.progress_pct.toFixed(1) + '%';
            document.getElementById('progress-fill').style.width = data.progress_pct + '%';
            document.getElementById('total-tasks').textContent = data.total_tasks;
            document.getElementById('completed-tasks').textContent = data.completed_tasks;
            document.getElementById('running-tasks').textContent = data.running_tasks;
            document.getElementById('failed-tasks').textContent = data.failed_tasks;
            
            // Update metrics based on benchmark type
            const benchmarkType = data.benchmark_type || 'default';
            const metricsContainer = document.getElementById('key-metrics');
            
            if (benchmarkType === 'gaia' || benchmarkType === 'default') {{
                // GAIA/Default: Show correctness metrics
                updateMetric('correct-answers', data.correct_answers || 0, 'Correct');
                updateMetric('incorrect-answers', data.incorrect_answers || 0, 'Incorrect');
                updateMetric('accuracy', (data.accuracy || 0).toFixed(1) + '%', 'Accuracy');
            }} else if (benchmarkType === 'futurex' || benchmarkType === 'xbench') {{
                // FutureX/xbench: Show prediction metrics
                updateMetric('with-predictions', data.with_predictions || 0, 'With Predictions');
                updateMetric('without-predictions', data.without_predictions || 0, 'Without Predictions');
                updateMetric('prediction-rate', (data.prediction_rate || 0).toFixed(1) + '%', 'Prediction Rate');
            }} else if (benchmarkType === 'finsearchcomp') {{
                // FinSearchComp: Show T2+T3 accuracy and task breakdown
                updateMetric('correct-answers', data.correct_answers || 0, 'Correct (T2+T3)');
                updateMetric('incorrect-answers', data.incorrect_answers || 0, 'Incorrect (T2+T3)');
                updateMetric('accuracy', (data.accuracy || 0).toFixed(1) + '%', 'Accuracy (T2+T3)');
                if (data.task_type_breakdown) {{
                    updateMetric('t1-completed', data.t1_completed || 0, 'T1 Completed');
                }}
            }}
        }}
        
        function updateMetric(id, value, label) {{
            let metricDiv = document.getElementById(id);
            if (!metricDiv) {{
                // Create metric if it doesn't exist
                const container = document.getElementById('key-metrics');
                metricDiv = document.createElement('div');
                metricDiv.className = 'metric';
                metricDiv.id = id;
                metricDiv.innerHTML = `
                    <div class="metric-value" id="${{id}}-value">0</div>
                    <div class="metric-label" id="${{id}}-label">${{label}}</div>
                `;
                container.appendChild(metricDiv);
            }}
            document.getElementById(id + '-value').textContent = value;
            document.getElementById(id + '-label').textContent = label;
        }}
        
        function updateTaskList(tasks, benchmarkType) {{
            const container = document.getElementById('task-list');
            container.innerHTML = '';
            tasks.forEach(task => {{
                const div = document.createElement('div');
                div.className = 'task-item';
                const taskTypeDisplay = task.task_type ? `<small>${{task.task_type}}</small>` : '';
                
                // Tailor display logic for each benchmark type (like check_*_progress.py)
                let judgeDisplay = '';
                if (benchmarkType === 'futurex' || benchmarkType === 'xbench') {{
                    // FutureX/xbench: Don't show judge_result, only show prediction status (like check_futurex_progress.py, check_xbench_progress.py)
                    if (task.final_answer && task.final_answer.trim()) {{
                        judgeDisplay = ' - Has Prediction';
                    }}
                }} else if (benchmarkType === 'gaia') {{
                    // GAIA: Show all judge_result (CORRECT/INCORRECT/other) (like check_gaia_progress.py)
                    if (task.judge_result && task.judge_result !== 'N/A') {{
                        judgeDisplay = ` - ${{task.judge_result}}`;
                    }}
                }} else if (benchmarkType === 'finsearchcomp') {{
                    // FinSearchComp: Show all judge_result including NOT_ATTEMPTED (like check_finsearchcomp_progress.py)
                    // Note: T1 tasks don't have judge_result, T2/T3 show judge_result
                    if (task.judge_result && task.judge_result !== 'N/A') {{
                        judgeDisplay = ` - ${{task.judge_result}}`;
                    }}
                }} else {{
                    // Default: Show judge_result if available
                    if (task.judge_result && task.judge_result !== 'N/A') {{
                        judgeDisplay = ` - ${{task.judge_result}}`;
                    }}
                }}
                
                div.innerHTML = `
                    <strong>${{task.task_id}}</strong> - 
                    <span class="status-${{task.status}}">${{task.status}}</span>${{judgeDisplay}}${{taskTypeDisplay ? ' - ' + taskTypeDisplay : ''}}
                    <button onclick="viewTaskReport('${{task.task_id}}')" class="view-report-btn">View Report</button>
                `;
                container.appendChild(div);
            }});
        }}
        
        function viewTaskReport(taskId) {{
            // Open task report in a new window
            window.open(`/api/task-report/${{taskId}}`, '_blank');
        }}
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Initial load
        window.onload = refreshData;
    </script>
</head>
<body>
    <div class="container">
        <h1>{benchmark_name} Monitor Dashboard</h1>
        
        <div class="card">
            <h2>Overall Progress</h2>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
            </div>
            <p>Progress: <span id="progress-pct">0%</span></p>
        </div>
        
        <div class="card">
            <h2>Key Metrics</h2>
            <div id="key-metrics">
                <div class="metric">
                    <div class="metric-value" id="total-tasks">0</div>
                    <div class="metric-label">Total Tasks</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="completed-tasks">0</div>
                    <div class="metric-label">Completed</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="running-tasks">0</div>
                    <div class="metric-label">Running</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="failed-tasks">0</div>
                    <div class="metric-label">Failed</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Tasks</h2>
            <button class="refresh-btn" onclick="refreshData()">Refresh</button>
            <div class="task-list" id="task-list">
                Loading...
            </div>
        </div>
    </div>
</body>
</html>
                """

        return DashboardHandler


class BenchmarkMonitor:
    """Generic benchmark monitor with web interface"""

    def __init__(self, log_folder: str):
        self.log_folder = Path(log_folder)
        self.start_time = datetime.now()
        self.benchmark_name = self._detect_benchmark_name()
        self.benchmark_type = self._detect_benchmark_type()

        # Initialize statistics based on benchmark type
        self.stats = self._initialize_stats()

        self.tasks = {}
        self.recent_activity = []

    def _detect_benchmark_name(self) -> str:
        """Detect benchmark name from log folder path or config file"""
        # Try to get from .hydra/config.yaml first
        hydra_config_path = self.log_folder / ".hydra" / "config.yaml"
        if hydra_config_path.exists():
            try:
                cfg = OmegaConf.load(hydra_config_path)
                benchmark_name = cfg.get("benchmark", {}).get("name", "")
                if benchmark_name:
                    return self._format_benchmark_name(benchmark_name)
            except Exception:
                pass
        
        # Try to extract from path (e.g., logs/gaia/... -> GAIA)
        path_parts = self.log_folder.parts
        if "logs" in path_parts:
            idx = path_parts.index("logs")
            if idx + 1 < len(path_parts):
                benchmark_name = path_parts[idx + 1]
                return self._format_benchmark_name(benchmark_name)
        
        # Default fallback
        return "Benchmark"
    
    def _format_benchmark_name(self, name: str) -> str:
        """Format benchmark name to a friendly display format"""
        name_lower = name.lower().replace("-", "").replace("_", "")
        
        # Map common benchmark names to their preferred display format
        name_mapping = {
            "finsearchcomp": "FinSearchComp",
            "futurex": "FutureX",
            "future-x": "FutureX",
            "gaia": "GAIA",
            "xbench": "xbench",
            "x-bench": "xbench",
            "browsecomp": "BrowseComp",
            "browsecomp-zh": "BrowseComp-ZH",
        }
        
        # Check exact match first
        if name_lower in name_mapping:
            return name_mapping[name_lower]
        
        # Check partial match (e.g., "finsearchcomp-claude" -> "FinSearchComp")
        for key, value in name_mapping.items():
            if name_lower.startswith(key):
                return value
        
        # Default: convert to title case (e.g., "example_dataset" -> "Example Dataset")
        return name.replace("-", " ").replace("_", " ").title()

    def _detect_benchmark_type(self) -> str:
        """Detect benchmark type to determine statistics logic"""
        name_lower = self.benchmark_name.lower()
        
        if "gaia" in name_lower:
            return "gaia"  # Has ground truth, needs correctness evaluation
        elif "futurex" in name_lower or "future-x" in name_lower:
            return "futurex"  # No ground truth, prediction-focused
        elif "xbench" in name_lower or "x-bench" in name_lower:
            return "xbench"  # No ground truth, prediction-focused
        elif "finsearchcomp" in name_lower or "finsearch-comp" in name_lower:
            return "finsearchcomp"  # Has ground truth, needs task type breakdown
        else:
            return "default"  # Default: assume has ground truth

    def _initialize_stats(self) -> Dict[str, Any]:
        """Initialize statistics based on benchmark type"""
        base_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "running_tasks": 0,
            "failed_tasks": 0,
            "execution_times": [],
            "error_types": {},
            "task_types": {},
            "last_update": None,
        }
        
        if self.benchmark_type == "gaia":
            # GAIA: correctness evaluation
            base_stats.update({
                "correct_answers": 0,
                "incorrect_answers": 0,
            })
        elif self.benchmark_type in ["futurex", "xbench"]:
            # FutureX/xbench: prediction-focused
            base_stats.update({
                "with_predictions": 0,
                "without_predictions": 0,
                "with_errors": 0,
            })
        elif self.benchmark_type == "finsearchcomp":
            # FinSearchComp: task type and regional breakdown (like check_finsearchcomp_progress.py)
            base_stats.update({
                "correct_answers": 0,  # T2+T3 only
                "incorrect_answers": 0,  # T2+T3 only
                "task_type_breakdown": {
                    "T1": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                    "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                    "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                    "Unknown": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                },
                "regional_breakdown": {
                    "Global": {
                        "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                        "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                    },
                    "Greater China": {
                        "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                        "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                    },
                },
            })
        else:
            # Default: assume has ground truth
            base_stats.update({
                "correct_answers": 0,
                "incorrect_answers": 0,
            })
        
        return base_stats

    def scan_log_files(self) -> List[Path]:
        """Scan for all task log files"""
        if not self.log_folder.exists():
            return []
        return sorted(
            self.log_folder.glob("task_*_attempt_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

    def parse_task_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single task log file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return None

    def extract_task_info(
        self, data: Dict[str, Any], file_path: Path
    ) -> Dict[str, Any]:
        """Extract relevant information from task data"""
        task_id = data.get("task_id", "unknown")
        status = data.get("status", "unknown").lower()
        judge_result = data.get("judge_result", "").upper()
        final_answer = data.get("final_boxed_answer", "")
        error_msg = data.get("error", "")
        
        # Extract attempt number from filename (e.g., task_xxx_attempt_1.json -> 1)
        attempt = 1  # Default
        match = re.search(r"_attempt_(\d+)\.json$", str(file_path))
        if match:
            attempt = int(match.group(1))

        # Extract execution time
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        execution_time = None

        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                execution_time = (end_dt - start_dt).total_seconds()
            except Exception:
                pass

        # Extract task type from metadata or task_id
        task_type = ""
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            # Try to get task type from various metadata fields
            if "Level" in metadata:
                task_type = f"Level {metadata['Level']}"
            elif "task_type" in metadata:
                task_type = str(metadata["task_type"])
            elif "type" in metadata:
                task_type = str(metadata["type"])
            elif "difficulty" in metadata:
                task_type = f"Difficulty {metadata['difficulty']}"
        
        # For FinSearchComp, extract task type from task_id (e.g., "(T1)Time_Sensitive_Data_Fetching_006")
        if self.benchmark_type == "finsearchcomp" and not task_type:
            match = re.match(r"^\(T(\d+)\)", task_id)
            if match:
                task_type = f"T{match.group(1)}"
        
        # Extract region for FinSearchComp
        region = ""
        if self.benchmark_type == "finsearchcomp":
            label = data.get("input", {}).get("metadata", {}).get("label", "")
            if "(Global)" in label:
                region = "Global"
            elif "(Greater China)" in label:
                region = "Greater China"

        return {
            "task_id": task_id,
            "file_path": str(file_path),
            "status": status,
            "judge_result": judge_result,
            "final_answer": final_answer,
            "error": error_msg,
            "execution_time": execution_time,
            "task_type": task_type,
            "region": region,
            "attempt": attempt,
            "last_modified": file_path.stat().st_mtime,
        }

    def update_statistics(self, task_info: Dict[str, Any]):
        """Update monitoring statistics based on benchmark type"""
        task_id = task_info["task_id"]
        status = task_info["status"]
        judge_result = task_info["judge_result"]
        execution_time = task_info["execution_time"]
        final_answer = task_info.get("final_answer", "")
        error_msg = task_info.get("error", "")
        task_type = task_info.get("task_type", "")

        # Update task tracking
        if task_id not in self.tasks:
            self.tasks[task_id] = task_info
            self.stats["total_tasks"] += 1
            region = task_info.get("region", "")
            self._update_stats_for_new_task(status, judge_result, final_answer, error_msg, task_type, region)
        else:
            # Update existing task - only update if status changed
            old_status = self.tasks[task_id]["status"]
            if old_status != status:
                self.recent_activity.append(
                    {
                        "task_id": task_id,
                        "old_status": old_status,
                        "new_status": status,
                        "timestamp": datetime.now(),
                    }
                )
                old_region = self.tasks[task_id].get("region", "")
                new_region = task_info.get("region", "")
                self._update_stats_for_status_change(
                    old_status, status, 
                    self.tasks[task_id].get("judge_result", ""),
                    judge_result,
                    self.tasks[task_id].get("final_answer", ""),
                    final_answer,
                    self.tasks[task_id].get("error", ""),
                    error_msg,
                    task_type,
                    old_region,
                    new_region
                )
            self.tasks[task_id] = task_info

        # Track execution times
        if execution_time is not None:
            self.stats["execution_times"].append(execution_time)
            if len(self.stats["execution_times"]) > 100:
                self.stats["execution_times"] = self.stats["execution_times"][-100:]

    def _update_stats_for_new_task(self, status: str, judge_result: str, 
                                   final_answer: str, error_msg: str, task_type: str, region: str = ""):
        """Update statistics for a new task based on benchmark type (like check_finsearchcomp_progress.py)"""
        if status == "completed":
            self.stats["completed_tasks"] += 1
            
            if self.benchmark_type == "gaia":
                if judge_result == "CORRECT":
                    self.stats["correct_answers"] += 1
                elif judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] += 1
            elif self.benchmark_type in ["futurex", "xbench"]:
                # For xbench/futurex: count predictions for all tasks (like check_xbench_progress.py)
                # But prediction_rate is calculated as with_predictions / completed
                pass  # Predictions and errors are counted below for all statuses
            elif self.benchmark_type == "finsearchcomp":
                if task_type in ["T1", "T2", "T3", "Unknown"]:
                    self.stats["task_type_breakdown"][task_type]["completed"] += 1
                
                # For T1 tasks, exclude from correctness evaluation (like check_finsearchcomp_progress.py)
                # T1 tasks are considered "completed" but not evaluated for correctness due to outdated ground truth
                if task_type == "T1":
                    pass  # T1 tasks are excluded from correctness evaluation
                elif task_type in ["T2", "T3"]:
                    # For T2 and T3 tasks, evaluate correctness (like check_finsearchcomp_progress.py)
                    # If judge_result is CORRECT, count as correct; otherwise (including NOT_ATTEMPTED) count as incorrect
                    if judge_result == "CORRECT":
                        self.stats["correct_answers"] += 1
                        self.stats["task_type_breakdown"][task_type]["correct"] += 1
                        # Update regional breakdown for correct T2 and T3 tasks
                        if region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][region][task_type]["correct"] += 1
                    else:
                        # All non-CORRECT results (including NOT_ATTEMPTED, INCORRECT, ERROR) count as incorrect
                        self.stats["incorrect_answers"] += 1
                        self.stats["task_type_breakdown"][task_type]["incorrect"] += 1
                        # Update regional breakdown for incorrect T2 and T3 tasks
                        if region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][region][task_type]["incorrect"] += 1
            else:  # default
                if judge_result == "CORRECT":
                    self.stats["correct_answers"] += 1
                elif judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] += 1
        elif status == "running":
            self.stats["running_tasks"] += 1
        elif status in ["failed", "error", "interrupted"]:
            self.stats["failed_tasks"] += 1
        
        # For xbench/futurex: count predictions and errors for ALL tasks (like check_xbench_progress.py)
        if self.benchmark_type in ["futurex", "xbench"]:
            if final_answer and final_answer.strip():
                self.stats["with_predictions"] += 1
            else:
                self.stats["without_predictions"] += 1
            if error_msg and error_msg.strip():
                self.stats["with_errors"] += 1
        
        # Update task type breakdown for FinSearchComp
        if self.benchmark_type == "finsearchcomp" and task_type:
            if task_type in ["T1", "T2", "T3", "Unknown"]:
                self.stats["task_type_breakdown"][task_type]["total"] += 1
                # Update regional breakdown for T2 and T3 tasks
                if task_type in ["T2", "T3"] and region in ["Global", "Greater China"]:
                    self.stats["regional_breakdown"][region][task_type]["total"] += 1
                    if status == "completed":
                        self.stats["regional_breakdown"][region][task_type]["completed"] += 1

    def _update_stats_for_status_change(self, old_status: str, new_status: str,
                                        old_judge_result: str, new_judge_result: str,
                                        old_final_answer: str, new_final_answer: str,
                                        old_error: str, new_error: str,
                                        task_type: str, old_region: str = "", new_region: str = ""):
        """Update statistics when task status changes"""
        # Decrease old status count
        if old_status == "completed":
            self.stats["completed_tasks"] -= 1
            if self.benchmark_type == "gaia":
                if old_judge_result == "CORRECT":
                    self.stats["correct_answers"] -= 1
                elif old_judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] -= 1
            elif self.benchmark_type in ["futurex", "xbench"]:
                # Predictions and errors are updated below for all statuses
                pass
            elif self.benchmark_type == "finsearchcomp":
                if task_type in ["T1", "T2", "T3", "Unknown"]:
                    self.stats["task_type_breakdown"][task_type]["completed"] -= 1
                # For T1 tasks, exclude from correctness evaluation (like check_finsearchcomp_progress.py)
                if task_type == "T1":
                    pass  # T1 tasks are excluded from correctness evaluation
                elif task_type in ["T2", "T3"]:
                    # Like check_finsearchcomp_progress.py: if CORRECT, count as correct; otherwise as incorrect
                    if old_judge_result == "CORRECT":
                        self.stats["correct_answers"] -= 1
                        self.stats["task_type_breakdown"][task_type]["correct"] -= 1
                        # Update regional breakdown for correct T2 and T3 tasks
                        if old_region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][old_region][task_type]["correct"] -= 1
                    else:
                        # All non-CORRECT results count as incorrect
                        self.stats["incorrect_answers"] -= 1
                        self.stats["task_type_breakdown"][task_type]["incorrect"] -= 1
                        # Update regional breakdown for incorrect T2 and T3 tasks
                        if old_region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][old_region][task_type]["incorrect"] -= 1
                    # Update regional breakdown for completed T2 and T3 tasks
                    if old_region in ["Global", "Greater China"]:
                        self.stats["regional_breakdown"][old_region][task_type]["completed"] -= 1
            else:  # default
                if old_judge_result == "CORRECT":
                    self.stats["correct_answers"] -= 1
                elif old_judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] -= 1
        elif old_status == "running":
            self.stats["running_tasks"] -= 1
        elif old_status in ["failed", "error", "interrupted"]:
            self.stats["failed_tasks"] -= 1

        # Increase new status count
        if new_status == "completed":
            self.stats["completed_tasks"] += 1
            if self.benchmark_type == "gaia":
                if new_judge_result == "CORRECT":
                    self.stats["correct_answers"] += 1
                elif new_judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] += 1
            elif self.benchmark_type in ["futurex", "xbench"]:
                # Predictions and errors are updated below for all statuses
                pass
            elif self.benchmark_type == "finsearchcomp":
                if task_type in ["T1", "T2", "T3", "Unknown"]:
                    self.stats["task_type_breakdown"][task_type]["completed"] += 1
                
                # For T1 tasks, exclude from correctness evaluation (like check_finsearchcomp_progress.py)
                # T1 tasks are considered "completed" but not evaluated for correctness due to outdated ground truth
                if task_type == "T1":
                    pass  # T1 tasks are excluded from correctness evaluation
                elif task_type in ["T2", "T3"]:
                    # For T2 and T3 tasks, evaluate correctness (like check_finsearchcomp_progress.py)
                    # If judge_result is CORRECT, count as correct; otherwise (including NOT_ATTEMPTED) count as incorrect
                    if new_judge_result == "CORRECT":
                        self.stats["correct_answers"] += 1
                        self.stats["task_type_breakdown"][task_type]["correct"] += 1
                        # Update regional breakdown for correct T2 and T3 tasks
                        if new_region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][new_region][task_type]["correct"] += 1
                    else:
                        # All non-CORRECT results (including NOT_ATTEMPTED, INCORRECT, ERROR) count as incorrect
                        self.stats["incorrect_answers"] += 1
                        self.stats["task_type_breakdown"][task_type]["incorrect"] += 1
                        # Update regional breakdown for incorrect T2 and T3 tasks
                        if new_region in ["Global", "Greater China"]:
                            self.stats["regional_breakdown"][new_region][task_type]["incorrect"] += 1
                    # Update regional breakdown for completed T2 and T3 tasks
                    if new_region in ["Global", "Greater China"]:
                        self.stats["regional_breakdown"][new_region][task_type]["completed"] += 1
            else:  # default
                if new_judge_result == "CORRECT":
                    self.stats["correct_answers"] += 1
                elif new_judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] += 1
        elif new_status == "running":
            self.stats["running_tasks"] += 1
        elif new_status in ["failed", "error", "interrupted"]:
            self.stats["failed_tasks"] += 1
        
        # For xbench/futurex: update predictions and errors for ALL statuses (like check_xbench_progress.py)
        if self.benchmark_type in ["futurex", "xbench"]:
            # Decrease old counts
            if old_final_answer and old_final_answer.strip():
                self.stats["with_predictions"] -= 1
            else:
                self.stats["without_predictions"] -= 1
            if old_error and old_error.strip():
                self.stats["with_errors"] -= 1
            
            # Increase new counts
            if new_final_answer and new_final_answer.strip():
                self.stats["with_predictions"] += 1
            else:
                self.stats["without_predictions"] += 1
            if new_error and new_error.strip():
                self.stats["with_errors"] += 1

    def get_status_json(self) -> Dict[str, Any]:
        """Get current status as JSON for web interface, based on benchmark type"""
        total = self.stats["total_tasks"]
        completed = self.stats["completed_tasks"]
        running = self.stats["running_tasks"]
        failed = self.stats["failed_tasks"]

        progress_pct = (completed / total * 100) if total > 0 else 0
        progress_pct = min(progress_pct, 100.0)  # Cap at 100%

        exec_times = self.stats["execution_times"]
        avg_execution_time = sum(exec_times) / len(exec_times) if exec_times else 0

        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        tasks_per_second = completed / elapsed_time if elapsed_time > 0 else 0

        result = {
            "total_tasks": total,
            "completed_tasks": completed,
            "running_tasks": running,
            "failed_tasks": failed,
            "progress_pct": progress_pct,
            "avg_execution_time": avg_execution_time,
            "tasks_per_second": tasks_per_second,
            "benchmark_type": self.benchmark_type,
            "last_update": self.stats["last_update"].isoformat()
            if self.stats["last_update"]
            else None,
        }

        # Add type-specific metrics
        if self.benchmark_type == "gaia":
            total_judged = self.stats["correct_answers"] + self.stats["incorrect_answers"]
            accuracy = (
                (self.stats["correct_answers"] / total_judged * 100)
                if total_judged > 0
                else 0
            )
            result.update({
                "correct_answers": self.stats["correct_answers"],
                "incorrect_answers": self.stats["incorrect_answers"],
                "accuracy": accuracy,
            })
        elif self.benchmark_type in ["futurex", "xbench"]:
            prediction_rate = (
                (self.stats["with_predictions"] / completed * 100)
                if completed > 0
                else 0
            )
            result.update({
                "with_predictions": self.stats["with_predictions"],
                "without_predictions": self.stats["without_predictions"],
                "with_errors": self.stats["with_errors"],
                "prediction_rate": prediction_rate,
            })
        elif self.benchmark_type == "finsearchcomp":
            t2_t3_completed = (
                self.stats["task_type_breakdown"]["T2"]["completed"]
                + self.stats["task_type_breakdown"]["T3"]["completed"]
            )
            t2_t3_correct = (
                self.stats["task_type_breakdown"]["T2"]["correct"]
                + self.stats["task_type_breakdown"]["T3"]["correct"]
            )
            accuracy = (
                (t2_t3_correct / t2_t3_completed * 100)
                if t2_t3_completed > 0
                else 0
            )
            result.update({
                "correct_answers": self.stats["correct_answers"],  # T2+T3 only
                "incorrect_answers": self.stats["incorrect_answers"],  # T2+T3 only
                "accuracy": accuracy,  # T2+T3 accuracy
                "task_type_breakdown": self.stats["task_type_breakdown"],
                "regional_breakdown": self.stats["regional_breakdown"],  # Like check_finsearchcomp_progress.py
                "t1_completed": self.stats["task_type_breakdown"]["T1"]["completed"],
            })
        else:  # default
            total_judged = self.stats["correct_answers"] + self.stats["incorrect_answers"]
            accuracy = (
                (self.stats["correct_answers"] / total_judged * 100)
                if total_judged > 0
                else 0
            )
            result.update({
                "correct_answers": self.stats["correct_answers"],
                "incorrect_answers": self.stats["incorrect_answers"],
                "accuracy": accuracy,
            })

        return result

    def get_tasks_json(self) -> List[Dict[str, Any]]:
        """Get tasks list as JSON for web interface"""
        tasks_list = []
        for task_info in sorted(
            self.tasks.values(), key=lambda x: x["last_modified"], reverse=True
        ):
            # For FutureX/xbench, don't include judge_result (like check_futurex_progress.py, check_xbench_progress.py)
            task_dict = {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "task_type": task_info["task_type"],
                "execution_time": task_info["execution_time"],
            }
            
            # Exclude judge_result for FutureX and xbench (like check_futurex_progress.py, check_xbench_progress.py)
            if self.benchmark_type not in ["futurex", "xbench"]:
                task_dict["judge_result"] = task_info["judge_result"]
            else:
                # For FutureX/xbench, include final_answer instead (for display purposes)
                task_dict["final_answer"] = task_info.get("final_answer", "")
            
            tasks_list.append(task_dict)
        
        return tasks_list

    def scan_and_update(self):
        """Scan log files and update statistics"""
        log_files = self.scan_log_files()

        for file_path in log_files:
            data = self.parse_task_file(file_path)
            if data:
                task_info = self.extract_task_info(data, file_path)
                self.update_statistics(task_info)

        self.stats["last_update"] = datetime.now()

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task"""
        return self.tasks.get(task_id)

    def generate_task_report(self, task_id: str) -> Optional[str]:
        """Generate report by calling the standalone report generator"""
        try:
            # Get task info to extract attempt number
            task_info = self.get_task_info(task_id)
            if not task_info:
                return f"Error: Task {task_id} not found"
            
            attempt = task_info.get("attempt", 1)
            
            # Import the report generator module
            import importlib.util
            report_generator_path = os.path.join(
                os.path.dirname(__file__), "generate_benchmark_report.py"
            )
            
            spec = importlib.util.spec_from_file_location(
                "generate_benchmark_report",
                report_generator_path,
            )
            if spec is None or spec.loader is None:
                return f"Error: Could not load report generator module"
            
            report_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(report_module)
            
            # Call the report generator
            report_path = report_module.generate_task_report_from_log(
                log_dir=str(self.log_folder),
                task_id=task_id,
                attempt=attempt,
                output_dir=None,  # Use default output directory
            )
            
            if report_path and os.path.exists(report_path):
                # Read and return the generated report
                with open(report_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            return f"Error: Failed to generate report for task {task_id}"
            
        except Exception as e:
            return f"Error generating report for task {task_id}: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="Benchmark Monitor with Web Interface")
    parser.add_argument("log_folder", nargs="?", default=".", help="Path to benchmark log folder")
    parser.add_argument("--web-port", type=int, default=8080, help="Web interface port")

    args = parser.parse_args()

    if not Path(args.log_folder).exists():
        print(f"Error: Log folder not found: {args.log_folder}")
        return 1

    # Create monitor
    monitor = BenchmarkMonitor(args.log_folder)

    # Start web dashboard
    dashboard = WebDashboard(monitor, args.web_port)
    dashboard.start_server()

    print("Benchmark Monitor started")
    print(f"Monitoring logs in: {args.log_folder}")
    print(f"Web dashboard: http://localhost:{dashboard.port}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            monitor.scan_and_update()
            time.sleep(30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")

    return 0


if __name__ == "__main__":
    exit(main())
