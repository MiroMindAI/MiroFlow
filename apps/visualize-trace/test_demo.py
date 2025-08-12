#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Script for testing Web Demo functionality
"""

import requests

BASE_URL = "http://127.0.0.1:5000"


def test_api_endpoints():
    """Test various API endpoints"""
    print("🔍 Testing Trace Analysis Web Demo")
    print("=" * 50)

    # 1. Test file list
    print("\n1. Getting file list...")
    try:
        response = requests.get(f"{BASE_URL}/api/list_files")
        if response.status_code == 200:
            files = response.json()
            print(f"✓ Found {len(files['files'])} files:")
            for file in files["files"]:
                print(f"  - {file}")
        else:
            print(f"✗ Failed to get file list: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

    # 2. Load file
    if files["files"]:
        file_path = files["files"][0]
        print(f"\n2. Loading file: {file_path}")

        load_response = requests.post(
            f"{BASE_URL}/api/load_trace", json={"file_path": file_path}
        )
        if load_response.status_code == 200:
            print("✓ File loaded successfully")
        else:
            print(f"✗ Failed to load file: {load_response.status_code}")
            return False

        # 3. Test basic information
        print("\n3. Getting basic information...")
        basic_info = requests.get(f"{BASE_URL}/api/basic_info")
        if basic_info.status_code == 200:
            info = basic_info.json()
            print(f"✓ Task ID: {info.get('task_id', 'N/A')}")
            print(f"✓ Status: {info.get('status', 'N/A')}")
            print(f"✓ Final answer: {info.get('final_boxed_answer', 'N/A')[:50]}...")
        else:
            print(f"✗ Failed to get basic information: {basic_info.status_code}")

        # 4. Test execution summary
        print("\n4. Getting execution summary...")
        summary_response = requests.get(f"{BASE_URL}/api/execution_summary")
        if summary_response.status_code == 200:
            summary = summary_response.json()
            print(f"✓ Total steps: {summary.get('total_steps', 0)}")
            print(f"✓ Tool calls: {summary.get('total_tool_calls', 0)}")
            print(f"✓ Browser sessions: {summary.get('browser_sessions_count', 0)}")
        else:
            print(f"✗ Failed to get execution summary: {summary_response.status_code}")

        # 5. Test execution flow
        print("\n5. Getting execution flow...")
        flow_response = requests.get(f"{BASE_URL}/api/execution_flow")
        if flow_response.status_code == 200:
            flow = flow_response.json()
            print(f"✓ Execution flow contains {len(flow)} steps")

            # Show summary of the first few steps
            for i, step in enumerate(flow[:3]):
                print(
                    f"  Step {i + 1}: {step['agent']} ({step['role']}) - {step['content_preview'][:50]}..."
                )
                if step["tool_calls"]:
                    for tool in step["tool_calls"]:
                        print(
                            f"    🛠️ Tool call: {tool['server_name']}.{tool['tool_name']}"
                        )
        else:
            print(f"✗ Failed to get execution flow: {flow_response.status_code}")

        # 6. Test performance summary
        print("\n6. Getting performance summary...")
        perf_response = requests.get(f"{BASE_URL}/api/performance_summary")
        if perf_response.status_code == 200:
            perf = perf_response.json()
            if perf:
                print(
                    f"✓ Total execution time: {perf.get('total_wall_time', 0):.2f} seconds"
                )
            else:
                print("✓ No performance data")
        else:
            print(f"✗ Failed to get performance summary: {perf_response.status_code}")

        print("\n" + "=" * 50)
        print("🎉 Testing completed!")
        print(f"📱 Web interface URL: {BASE_URL}")
        print(
            "💡 Open the above URL in your browser to view the complete interactive interface"
        )

        return True

    else:
        print("✗ No available trace files found")
        return False


if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\n🚀 Web Demo started successfully!")
        print(
            "You can now access http://127.0.0.1:5000 in your browser to use the complete interactive interface"
        )
    else:
        print("\n❌ Test failed, please check if the application is running")
