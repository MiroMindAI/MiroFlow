#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
测试Web Demo功能的脚本
"""

import requests

BASE_URL = "http://127.0.0.1:5000"


def test_api_endpoints():
    """测试各个API端点"""
    print("🔍 测试 Trace Analysis Web Demo")
    print("=" * 50)

    # 1. 测试文件列表
    print("\n1. 获取文件列表...")
    try:
        response = requests.get(f"{BASE_URL}/api/list_files")
        if response.status_code == 200:
            files = response.json()
            print(f"✓ 找到 {len(files['files'])} 个文件:")
            for file in files["files"]:
                print(f"  - {file}")
        else:
            print(f"✗ 获取文件列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False

    # 2. 加载文件
    if files["files"]:
        file_path = files["files"][0]
        print(f"\n2. 加载文件: {file_path}")

        load_response = requests.post(
            f"{BASE_URL}/api/load_trace", json={"file_path": file_path}
        )
        if load_response.status_code == 200:
            print("✓ 文件加载成功")
        else:
            print(f"✗ 文件加载失败: {load_response.status_code}")
            return False

        # 3. 测试基本信息
        print("\n3. 获取基本信息...")
        basic_info = requests.get(f"{BASE_URL}/api/basic_info")
        if basic_info.status_code == 200:
            info = basic_info.json()
            print(f"✓ 任务ID: {info.get('task_id', 'N/A')}")
            print(f"✓ 状态: {info.get('status', 'N/A')}")
            print(f"✓ 最终答案: {info.get('final_boxed_answer', 'N/A')[:50]}...")
        else:
            print(f"✗ 获取基本信息失败: {basic_info.status_code}")

        # 4. 测试执行摘要
        print("\n4. 获取执行摘要...")
        summary_response = requests.get(f"{BASE_URL}/api/execution_summary")
        if summary_response.status_code == 200:
            summary = summary_response.json()
            print(f"✓ 总步骤数: {summary.get('total_steps', 0)}")
            print(f"✓ 工具调用次数: {summary.get('total_tool_calls', 0)}")
            print(f"✓ Browser会话数: {summary.get('browser_sessions_count', 0)}")
        else:
            print(f"✗ 获取执行摘要失败: {summary_response.status_code}")

        # 5. 测试执行流程
        print("\n5. 获取执行流程...")
        flow_response = requests.get(f"{BASE_URL}/api/execution_flow")
        if flow_response.status_code == 200:
            flow = flow_response.json()
            print(f"✓ 执行流程包含 {len(flow)} 个步骤")

            # 显示前几个步骤的摘要
            for i, step in enumerate(flow[:3]):
                print(
                    f"  步骤 {i+1}: {step['agent']} ({step['role']}) - {step['content_preview'][:50]}..."
                )
                if step["tool_calls"]:
                    for tool in step["tool_calls"]:
                        print(
                            f"    🛠️ 工具调用: {tool['server_name']}.{tool['tool_name']}"
                        )
        else:
            print(f"✗ 获取执行流程失败: {flow_response.status_code}")

        # 6. 测试性能摘要
        print("\n6. 获取性能摘要...")
        perf_response = requests.get(f"{BASE_URL}/api/performance_summary")
        if perf_response.status_code == 200:
            perf = perf_response.json()
            if perf:
                print(f"✓ 总执行时间: {perf.get('total_wall_time', 0):.2f}秒")
            else:
                print("✓ 无性能数据")
        else:
            print(f"✗ 获取性能摘要失败: {perf_response.status_code}")

        print("\n" + "=" * 50)
        print("🎉 测试完成！")
        print(f"📱 Web界面地址: {BASE_URL}")
        print("💡 在浏览器中打开上述地址以查看完整的交互界面")

        return True

    else:
        print("✗ 没有找到可用的trace文件")
        return False


if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\n🚀 Web Demo 启动成功！")
        print("现在可以在浏览器中访问 http://127.0.0.1:5000 来使用完整的交互界面")
    else:
        print("\n❌ 测试失败，请检查应用是否正在运行")
