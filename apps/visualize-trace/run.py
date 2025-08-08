#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Trace Analysis Web Demo 启动脚本
"""

import os
import sys
import subprocess


def check_dependencies():
    """检查依赖是否已安装"""
    try:
        import importlib.util

        if importlib.util.find_spec("flask") is not None:
            print("✓ Flask 已安装")
            return True
        else:
            raise ImportError("Flask not found")
    except ImportError:
        print("✗ Flask 未安装")
        print("请使用以下命令安装依赖:")
        print("  uv sync")
        print("或者:")
        print("  uv pip install -r requirements.txt")
        return False


def install_dependencies():
    """安装依赖（建议使用uv）"""
    print("正在安装依赖...")
    try:
        # 优先尝试使用uv
        try:
            subprocess.check_call(["uv", "sync"])
            print("✓ 使用uv安装依赖完成")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 回退到pip
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            )
            print("✓ 使用pip安装依赖完成")
            return True
    except subprocess.CalledProcessError:
        print("✗ 依赖安装失败")
        print("请手动运行: uv sync 或 pip install -r requirements.txt")
        return False


def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Trace Analysis Web Demo")
    parser.add_argument(
        "-p", "--port", type=int, default=5000, help="指定端口号 (默认: 5000)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Trace Analysis Web Demo")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        print("\n正在安装依赖...")
        if not install_dependencies():
            print("请手动安装依赖: pip install -r requirements.txt")
            return

    # 检查JSON文件
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = [
        f for f in os.listdir(os.path.join(parent_dir, "..")) if f.endswith(".json")
    ]

    if not json_files:
        print("\n警告: 在上级目录中没有找到JSON文件")
        print("请确保有trace JSON文件在 trace_analyze/ 目录中")
    else:
        print(f"\n找到 {len(json_files)} 个JSON文件:")
        for file in json_files[:5]:  # 只显示前5个
            print(f"  - {file}")
        if len(json_files) > 5:
            print(f"  ... 和其他 {len(json_files) - 5} 个文件")

    # 启动应用
    print("\n正在启动Web应用...")
    print(f"应用将在 http://localhost:{args.port} 运行")
    print("按 Ctrl+C 停止应用")
    print("=" * 50)

    try:
        from app import app

        app.run(debug=True, host="0.0.0.0", port=args.port)
    except KeyboardInterrupt:
        print("\n应用已停止")
    except Exception as e:
        print(f"\n启动应用失败: {e}")


if __name__ == "__main__":
    main()
