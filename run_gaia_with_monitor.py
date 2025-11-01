# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import signal
import sys
import time
from typing import Optional


def main(*args, config_file_name: str = "", output_dir: str = "", web_port: int = 8080):
    """Run benchmark with integrated web monitoring"""
    
    # Validate required arguments
    if not output_dir:
        print("Error: output_dir is required")
        print("Usage: uv run main.py run-gaia-with-monitor --output_dir=path --config_file_name=name")
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 50)
    print("Benchmark Runner with Monitor")
    print("=" * 50)
    print(f"Output directory: {output_dir}")
    print(f"Config name: {config_file_name}")
    print(f"Web port: {web_port}")
    print("=" * 50)
    
    # Global variables for process management
    benchmark_process: Optional[subprocess.Popen] = None
    monitor_process: Optional[subprocess.Popen] = None
    
    def cleanup_processes():
        """Clean up running processes"""
        print("\nShutting down processes...")
        
        if benchmark_process and benchmark_process.poll() is None:
            print(f"Stopping benchmark (PID: {benchmark_process.pid})...")
            benchmark_process.terminate()
            try:
                benchmark_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                benchmark_process.kill()
        
        if monitor_process and monitor_process.poll() is None:
            print(f"Stopping monitor (PID: {monitor_process.pid})...")
            monitor_process.terminate()
            try:
                monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                monitor_process.kill()
        
        print("Cleanup complete.")
    
    def signal_handler(signum, frame):
        """Handle Ctrl+C gracefully"""
        cleanup_processes()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start benchmark
        print("Starting benchmark...")
        benchmark_cmd = [
            "uv", "run", "main.py", "common-benchmark",
            f"--config_file_name={config_file_name}",
            f"output_dir={output_dir}"
        ]
        benchmark_process = subprocess.Popen(benchmark_cmd)
        print(f"Benchmark started with PID: {benchmark_process.pid}")
        
        # Wait a moment for benchmark to initialize
        time.sleep(3)
        
        # Start monitor
        print("Starting web monitor...")
        monitor_cmd = [
            "uv", "run", "utils/progress_check/gaia_web_monitor.py",
            output_dir,
            f"--web-port={web_port}"
        ]
        monitor_process = subprocess.Popen(monitor_cmd)
        print(f"Monitor started with PID: {monitor_process.pid}")
        print(f"Web dashboard available at: http://localhost:{web_port}")
        
        print("\n" + "=" * 50)
        print("Both processes are running!")
        print("Press Ctrl+C to stop both processes")
        print("Monitor will continue running even if benchmark finishes")
        print("=" * 50)
        
        # Monitor the processes
        while True:
            time.sleep(5)
            
            # Check if benchmark process is still running
            if benchmark_process and benchmark_process.poll() is not None:
                print("Benchmark process ended")
                benchmark_process = None
            
            # Check if monitor process is still running
            if monitor_process and monitor_process.poll() is not None:
                print("Monitor process died unexpectedly. Restarting...")
                monitor_process = subprocess.Popen(monitor_cmd)
                print(f"Monitor restarted with PID: {monitor_process.pid}")
    
    except KeyboardInterrupt:
        cleanup_processes()
    
    return 0


if __name__ == "__main__":
    import fire
    fire.Fire(main)
