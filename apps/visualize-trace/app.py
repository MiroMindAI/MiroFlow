# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from flask import Flask, render_template, jsonify, request
import os
from trace_analyzer import TraceAnalyzer

app = Flask(__name__)

# Global variable to store analyzer instance
analyzer = None


@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


@app.route("/api/list_files", methods=["GET"])
def list_files():
    """列出可用的JSON文件"""
    try:
        directory = request.args.get("directory", "")

        if not directory:
            # Default behavior: check parent directory
            directory = os.path.abspath("..")

        # Expand path (handle ~ and other symbols)
        directory = os.path.expanduser(directory)

        # Convert to absolute path
        directory = os.path.abspath(directory)

        if not os.path.exists(directory):
            return jsonify({"error": f"目录不存在: {directory}"}), 404

        if not os.path.isdir(directory):
            return jsonify({"error": f"路径不是目录: {directory}"}), 400

        try:
            json_files = []
            for file in os.listdir(directory):
                if file.endswith(".json"):
                    file_path = os.path.join(directory, file)
                    try:
                        # Get file size and modification time
                        stat = os.stat(file_path)
                        json_files.append(
                            {
                                "name": file,
                                "path": file_path,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                            }
                        )
                    except Exception:
                        json_files.append(
                            {"name": file, "path": file_path, "size": 0, "modified": 0}
                        )

            # Sort by filename
            json_files.sort(key=lambda x: x["name"])

            return jsonify(
                {
                    "files": json_files,
                    "directory": directory,
                    "message": f'在目录 "{directory}" 中找到 {len(json_files)} 个JSON文件',
                }
            )
        except PermissionError:
            return jsonify({"error": f"没有权限访问目录: {directory}"}), 403
        except Exception as e:
            return jsonify({"error": f"读取目录失败: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_trace", methods=["POST"])
def load_trace():
    """加载trace文件"""
    global analyzer

    data = request.get_json()
    file_path = data.get("file_path")

    if not file_path:
        return jsonify({"error": "请提供文件路径"}), 400

    # If it's a relative path, convert to absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        return jsonify({"error": f"文件不存在: {file_path}"}), 404

    try:
        analyzer = TraceAnalyzer(file_path)
        return jsonify(
            {
                "message": "文件加载成功",
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
            }
        )
    except Exception as e:
        return jsonify({"error": f"加载文件失败: {str(e)}"}), 500


@app.route("/api/basic_info")
def get_basic_info():
    """获取基本信息"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.get_basic_info())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/performance_summary")
def get_performance_summary():
    """获取性能摘要"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.get_performance_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/execution_flow")
def get_execution_flow():
    """获取执行流程"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.analyze_conversation_flow())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/execution_summary")
def get_execution_summary():
    """获取执行摘要"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.get_execution_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/spans_summary")
def get_spans_summary():
    """获取spans摘要"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.get_spans_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/step_logs_summary")
def get_step_logs_summary():
    """获取步骤日志摘要"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        return jsonify(analyzer.get_step_logs_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug/raw_messages")
def get_raw_messages():
    """获取原始消息数据用于调试"""
    if not analyzer:
        return jsonify({"error": "请先加载trace文件"}), 400

    try:
        main_history = analyzer.get_main_agent_history()
        browser_sessions = analyzer.get_browser_agent_sessions()

        # Get message structure overview
        main_messages = analyzer.get_main_agent_messages()
        message_structure = []

        for i, message in enumerate(main_messages):
            message_structure.append(
                {
                    "index": i,
                    "role": message.get("role"),
                    "content_length": len(str(message.get("content", ""))),
                    "has_timestamp": "timestamp" in message,
                    "content_preview": str(message.get("content", ""))[:100] + "..."
                    if len(str(message.get("content", ""))) > 100
                    else str(message.get("content", "")),
                }
            )

        return jsonify(
            {
                "main_agent_history_structure": {
                    "total_messages": len(main_messages),
                    "messages": message_structure,
                },
                "browser_sessions": list(browser_sessions.keys()),
                "raw_main_history": main_history,
                "raw_browser_sessions": {
                    k: v for k, v in list(browser_sessions.items())[:2]
                },  # 只显示前两个会话
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
