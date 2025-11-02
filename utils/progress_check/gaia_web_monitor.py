"""
GAIA Benchmark Monitor with Web Interface

This script provides monitoring capabilities including:
- Real-time web dashboard
- Historical data tracking

Usage:
    uv run utils/progress_check/gaia_web_monitor.py [LOG_FOLDER_PATH] [OPTIONS]

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
from http.server import HTTPServer, BaseHTTPRequestHandler


class WebDashboard:
    """Simple web dashboard for monitoring"""

    def __init__(self, monitor, port: int = 8080):
        self.monitor = monitor
        self.port = port
        self.server = None

    def start_server(self):
        """Start the web server"""
        handler = self.create_handler()
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

                    # Generate report using the generate_gaia_report script
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
                return """
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Monitor Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; color: #1976d2; }
        .metric-label { font-size: 14px; color: #666; }
        .progress-bar { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); transition: width 0.3s; }
        .status-running { color: #ff9800; }
        .status-completed { color: #4caf50; }
        .status-failed { color: #f44336; }
        .task-list { max-height: 400px; overflow-y: auto; }
        .task-item { padding: 8px; border-bottom: 1px solid #eee; }
        .refresh-btn { background: #2196f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .refresh-btn:hover { background: #1976d2; }
        .view-report-btn { background: #4caf50; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 10px; font-size: 12px; }
        .view-report-btn:hover { background: #45a049; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDashboard(data));
            
            fetch('/api/tasks')
                .then(response => response.json())
                .then(data => updateTaskList(data));
        }
        
        function updateDashboard(data) {
            document.getElementById('progress-pct').textContent = data.progress_pct.toFixed(1) + '%';
            document.getElementById('progress-fill').style.width = data.progress_pct + '%';
            document.getElementById('total-tasks').textContent = data.total_tasks;
            document.getElementById('completed-tasks').textContent = data.completed_tasks;
            document.getElementById('running-tasks').textContent = data.running_tasks;
            document.getElementById('failed-tasks').textContent = data.failed_tasks;
            document.getElementById('accuracy').textContent = data.accuracy.toFixed(1) + '%';
        }
        
        function updateTaskList(tasks) {
            const container = document.getElementById('task-list');
            container.innerHTML = '';
            tasks.forEach(task => {
                const div = document.createElement('div');
                div.className = 'task-item';
                const taskTypeDisplay = task.task_type ? `<small>${task.task_type}</small>` : '';
                div.innerHTML = `
                    <strong>${task.task_id}</strong> - 
                    <span class="status-${task.status}">${task.status}</span> - 
                    ${task.judge_result}${taskTypeDisplay ? ' - ' + taskTypeDisplay : ''}
                    <button onclick="viewTaskReport('${task.task_id}')" class="view-report-btn">View Report</button>
                `;
                container.appendChild(div);
            });
        }
        
        function viewTaskReport(taskId) {
            // Open task report in a new window
            window.open(`/api/task-report/${taskId}`, '_blank');
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Initial load
        window.onload = refreshData;
    </script>
</head>
<body>
    <div class="container">
        <h1>Benchmark Monitor Dashboard</h1>
        
        <div class="card">
            <h2>Overall Progress</h2>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
            </div>
            <p>Progress: <span id="progress-pct">0%</span></p>
        </div>
        
        <div class="card">
            <h2>Key Metrics</h2>
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
            <div class="metric">
                <div class="metric-value" id="accuracy">0%</div>
                <div class="metric-label">Accuracy</div>
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


class AdvancedBenchmarkMonitor:
    """GAIA benchmark monitor with web interface"""

    def __init__(self, log_folder: str):
        self.log_folder = Path(log_folder)
        self.start_time = datetime.now()
        # Alerts removed per user request

        # Statistics tracking
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "running_tasks": 0,
            "failed_tasks": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "execution_times": [],
            "error_types": {},
            "task_types": {},
            "last_update": None,
        }

        self.tasks = {}
        self.recent_activity = []
        self._generate_gaia_report_module = None

    def _load_generate_gaia_report_module(self):
        """Lazy load the generate_gaia_report module"""
        if self._generate_gaia_report_module is None:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "generate_gaia_report",
                os.path.join(os.path.dirname(__file__), "generate_gaia_report.py"),
            )
            if spec is None or spec.loader is None:
                return None
            self._generate_gaia_report_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self._generate_gaia_report_module)
        return self._generate_gaia_report_module

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

        # Extract task type from metadata
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

        return {
            "task_id": task_id,
            "file_path": str(file_path),
            "status": status,
            "judge_result": judge_result,
            "final_answer": final_answer,
            "error": error_msg,
            "execution_time": execution_time,
            "task_type": task_type,
            "last_modified": file_path.stat().st_mtime,
        }

    def update_statistics(self, task_info: Dict[str, Any]):
        """Update monitoring statistics and check for alerts"""
        task_id = task_info["task_id"]
        status = task_info["status"]
        judge_result = task_info["judge_result"]
        execution_time = task_info["execution_time"]

        # Update task tracking
        if task_id not in self.tasks:
            self.tasks[task_id] = task_info
            self.stats["total_tasks"] += 1
            # Only count status for new tasks
            if status == "completed":
                self.stats["completed_tasks"] += 1
                if judge_result == "CORRECT":
                    self.stats["correct_answers"] += 1
                elif judge_result in ["INCORRECT", "ERROR"]:
                    self.stats["incorrect_answers"] += 1
            elif status == "running":
                self.stats["running_tasks"] += 1
            elif status in ["failed", "error", "interrupted"]:
                self.stats["failed_tasks"] += 1
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

                # Decrease old status count
                if old_status == "completed":
                    self.stats["completed_tasks"] -= 1
                    old_judge_result = self.tasks[task_id]["judge_result"]
                    if old_judge_result == "CORRECT":
                        self.stats["correct_answers"] -= 1
                    elif old_judge_result in ["INCORRECT", "ERROR"]:
                        self.stats["incorrect_answers"] -= 1
                elif old_status == "running":
                    self.stats["running_tasks"] -= 1
                elif old_status in ["failed", "error", "interrupted"]:
                    self.stats["failed_tasks"] -= 1

                # Increase new status count
                if status == "completed":
                    self.stats["completed_tasks"] += 1
                    if judge_result == "CORRECT":
                        self.stats["correct_answers"] += 1
                    elif judge_result in ["INCORRECT", "ERROR"]:
                        self.stats["incorrect_answers"] += 1
                elif status == "running":
                    self.stats["running_tasks"] += 1
                elif status in ["failed", "error", "interrupted"]:
                    self.stats["failed_tasks"] += 1

            self.tasks[task_id] = task_info

        # Track execution times
        if execution_time is not None:
            self.stats["execution_times"].append(execution_time)
            if len(self.stats["execution_times"]) > 100:
                self.stats["execution_times"] = self.stats["execution_times"][-100:]

        # Alerts removed; no checks performed

    def get_status_json(self) -> Dict[str, Any]:
        """Get current status as JSON for web interface"""
        total = self.stats["total_tasks"]
        completed = self.stats["completed_tasks"]
        running = self.stats["running_tasks"]
        failed = self.stats["failed_tasks"]

        progress_pct = (completed / total * 100) if total > 0 else 0
        progress_pct = min(progress_pct, 100.0)  # Cap at 100%

        total_judged = self.stats["correct_answers"] + self.stats["incorrect_answers"]
        accuracy = (
            (self.stats["correct_answers"] / total_judged * 100)
            if total_judged > 0
            else 0
        )

        exec_times = self.stats["execution_times"]
        avg_execution_time = sum(exec_times) / len(exec_times) if exec_times else 0

        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        tasks_per_second = completed / elapsed_time if elapsed_time > 0 else 0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "running_tasks": running,
            "failed_tasks": failed,
            "progress_pct": progress_pct,
            "accuracy": accuracy,
            "avg_execution_time": avg_execution_time,
            "tasks_per_second": tasks_per_second,
            "last_update": self.stats["last_update"].isoformat()
            if self.stats["last_update"]
            else None,
        }

    def get_tasks_json(self) -> List[Dict[str, Any]]:
        """Get tasks list as JSON for web interface"""
        return [
            {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "judge_result": task_info["judge_result"],
                "task_type": task_info["task_type"],
                "execution_time": task_info["execution_time"],
            }
            for task_info in sorted(
                self.tasks.values(), key=lambda x: x["last_modified"], reverse=True
            )
        ]

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
        """Generate the original simple report (no execution details)."""
        try:
            # Import the original report generator (now in the same directory)
            generate_module = self._load_generate_gaia_report_module()
            if generate_module is None:
                return None
            generate_task_report = generate_module.generate_task_report

            # Map task_id to dataset index
            task_index = self.find_task_index_in_dataset(task_id)
            if task_index is None:
                return None

            # Generate and return the plain report content
            report_path = generate_task_report(task_index)
            if report_path and os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None

        except Exception as e:
            print(f"Error generating simple report for task {task_id}: {e}")
            return None

    def find_task_index_in_dataset(self, task_id: str) -> Optional[int]:
        """Find the index of a task in the GAIA dataset"""
        try:
            # Import from the same directory
            generate_module = self._load_generate_gaia_report_module()
            if generate_module is None:
                return None
            load_gaia_data = generate_module.load_gaia_data

            # Load GAIA data
            tasks = load_gaia_data()

            # Find the task by ID
            for i, task in enumerate(tasks):
                if task.get("task_id") == task_id:
                    return i

            return None

        except Exception as e:
            print(f"Error finding task {task_id} in dataset: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="GAIA Benchmark Monitor")
    parser.add_argument("log_folder", nargs="?", default=".", help="Path to log folder")
    parser.add_argument("--web-port", type=int, default=8080, help="Web interface port")
    # Alert functionality removed; threshold flag no longer supported

    args = parser.parse_args()

    if not Path(args.log_folder).exists():
        print(f"Error: Log folder not found: {args.log_folder}")
        return 1

    # Create monitor
    monitor = AdvancedBenchmarkMonitor(args.log_folder)

    # Start web dashboard
    dashboard = WebDashboard(monitor, args.web_port)
    dashboard.start_server()

    print("GAIA Benchmark Monitor started")
    print(f"Web dashboard: http://localhost:{args.web_port}")
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
