import json
import os
import shutil
import re
from flask import Flask, request, jsonify, render_template, Response
from openai import OpenAI
from config import MODELS, save_models

# 文件操作支持
ALLOWED_ROOT = os.path.expanduser("~")
current_work_dir = "/Users/niuzilin/VSCodeProjects/Test01"

# 权限管理：存储用户授权的路径
authorized_paths = {ALLOWED_ROOT}  # 默认允许用户主目录

def is_path_authorized(path):
    """检查路径是否在已授权范围内"""
    real_path = os.path.realpath(path)
    for auth_path in authorized_paths:
        if real_path.startswith(os.path.realpath(auth_path)):
            return True
    return False

def request_path_authorization(path):
    """请求路径授权（返回提示信息）"""
    real_path = os.path.realpath(path)
    return (
        f"⚠️ 该路径需要授权访问：{real_path}\n\n"
        f"该路径不在已授权范围内。如需访问，请输入：\n"
        f"授权 {real_path}"
    )

def safe_path(target):
    """安全路径解析，返回真实路径"""
    joined = os.path.join(current_work_dir, target)
    return os.path.realpath(joined)


def handle_file_command(cmd, user_message):
    """处理文件操作命令，返回 (response_text, is_command) 元组"""
    global current_work_dir
    msg = user_message.strip()

    # 授权路径: 授权 <path>
    m = re.match(r'^授权\s+(.+)$', msg)
    if m:
        target = m.group(1).strip()
        real_path = os.path.realpath(target)
        if not os.path.exists(real_path):
            return f"❌ 路径不存在: {real_path}", True
        authorized_paths.add(real_path)
        return f"✅ 已授权访问：{real_path}\n当前已授权路径数量：{len(authorized_paths)}", True

    # 查看已授权路径: 已授权路径 或 授权列表
    if msg in ('已授权路径', '授权列表', 'authorized'):
        lines = ["📋 已授权访问的路径：", ""]
        for i, path in enumerate(sorted(authorized_paths), 1):
            lines.append(f"{i}. {path}")
        return "\n".join(lines), True

    # 进入/切换到目录: 进入 <path> 或 cd <path> 或 切换到 <path>
    m = re.match(r'^(进入到?|切换到|cd)\s*(.+?)(?:目录)?$', msg)
    if m:
        target = m.group(2).strip().rstrip('目录')
        # 如果目标是绝对路径（以 / 开头），直接使用
        if target.startswith('/'):
            target_path = target
        else:
            # 相对路径，基于当前工作目录
            target_path = os.path.join(current_work_dir, target)
        # 解析为真实路径（处理 .. 和符号链接）
        real = os.path.realpath(target_path)
        if not os.path.isdir(real):
            return f"❌ 目录不存在: {target}", True
        # 检查权限
        if not is_path_authorized(real):
            return request_path_authorization(real), True
        current_work_dir = real
        return f"✅ 已切换到目录：{current_work_dir}", True

    # 查看当前路径: 当前路径 或 pwd
    if msg in ('当前路径', 'pwd', 'pwd()'):
        return f"📂 当前路径: {current_work_dir}", True

    # 列出目录: 列出 或 ls
    if msg in ('列出', 'ls', 'list'):
        # 检查权限
        if not is_path_authorized(current_work_dir):
            return request_path_authorization(current_work_dir), True
        try:
            items = os.listdir(current_work_dir)
            lines = [f"📁 {current_work_dir}", "", "内容:"]
            for item in sorted(items):
                full_path = os.path.join(current_work_dir, item)
                if os.path.isdir(full_path):
                    lines.append(f"  📁  {item}/")
                else:
                    size = os.path.getsize(full_path)
                    lines.append(f"  📄  {item} ({size} bytes)")
            return "\n".join(lines) if lines else "(空目录)", True
        except PermissionError:
            return "❌ 系统拒绝访问（权限不足）", True

    # 查看文件: 查看 <file> 或 cat <file>
    m = re.match(r'^(查看|cat|open|读取)\s+(.+)$', msg)
    if m:
        filename = m.group(2).strip()
        target_path = safe_path(filename)
        # 检查权限
        if not is_path_authorized(target_path):
            return request_path_authorization(target_path), True
        if not os.path.isfile(target_path):
            return f"❌ 文件不存在: {target_path}", True
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            max_len = 100000
            if len(file_content) > max_len:
                file_content = file_content[:max_len] + "\n\n... 文件过大，仅显示前100KB"
            return f"📄 文件: {target_path}\n\n{file_content}", True
        except UnicodeDecodeError:
            return f"❌ 无法以文本方式读取该文件（可能为二进制文件）", True
        except PermissionError:
            return f"❌ 系统拒绝访问（权限不足）", True
        except Exception as e:
            return f"❌ 读取失败: {str(e)}", True

    # 查找文件: 查找 <pattern> 或 find <pattern>
    m = re.match(r'^(查找|find|search)\s+(.+)$', msg)
    if m:
        pattern = m.group(2).strip()
        # 检查权限
        if not is_path_authorized(current_work_dir):
            return request_path_authorization(current_work_dir), True
        results = []
        try:
            for root, dirs, files in os.walk(current_work_dir):
                for f in files:
                    if pattern in f:
                        results.append(os.path.join(root, f))
                if root.count(os.sep) - current_work_dir.count(os.sep) > 3:
                    dirs.clear()
            if results:
                return f"🔍 找到 {len(results)} 个匹配文件:\n" + "\n".join(results[:50]), True
            else:
                return "🔍 未找到匹配的文件", True
        except Exception as e:
            return f"❌ 查找失败: {str(e)}", True

    # 不是文件命令
    return None, False


app = Flask(__name__)

# 按模型隔离对话历史: {model_key: [messages]}
conversations = {}

# 预设提示词模板
PROMPT_TEMPLATES = [
    {"name": "📝 代码审查", "prompt": "请审查以下代码，指出潜在问题、性能优化建议和安全漏洞：\n\n"},
    {"name": "✍️ 总结", "prompt": "请用简洁的语言总结以下内容的核心要点：\n\n"},
    {"name": "🐛 Bug 修复", "prompt": "请帮我找找这个代码中的 bug 并给出修复方案：\n\n"},
    {"name": "💡 解释代码", "prompt": "请逐行解释以下代码的工作原理：\n\n"},
    {"name": "📄 写邮件", "prompt": "请帮我起草一封专业的邮件，主题为："},
    {"name": "🎨 翻译", "prompt": "请将以下内容翻译成英文：\n\n"},
    {"name": "📊 数据分析建议", "prompt": "针对以下数据/场景，请给出数据分析方案和建议：\n\n"},
    {"name": "🔧 优化建议", "prompt": "请分析以下内容并提供优化建议：\n\n"},
]


def get_history(model_key):
    """获取指定模型的对话历史"""
    if model_key not in conversations:
        conversations[model_key] = []
    return conversations[model_key]


def get_client(model_key):
    """根据模型 key 获取 OpenAI 客户端"""
    cfg = MODELS.get(model_key)
    if not cfg:
        return None
    return OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["api_base"],
    )


def build_messages(model_key, user_message):
    """构建消息列表，包含模型身份标识"""
    cfg = MODELS.get(model_key, {})
    model_display_name = cfg.get("name", model_key)
    model_api_name = cfg.get("model", "")

    system_content = (
        f"你是一个有用的AI助手，具备文件系统访问能力。"
        f"你当前正在被调用的模型是：{model_display_name}（API模型名：{model_api_name}）。"
        f"如果用户问你在用什么模型，请如实回答你正在被调用的模型名称。"
        f"\n\n## 文件操作能力\n"
        f"当用户询问文件或目录时，你可以直接使用命令查看，而不是说无法访问。\n"
        f"当前工作目录：{current_work_dir}\n"
        f"已授权路径：{', '.join(sorted(authorized_paths))}\n"
        f"\n你需要直接在回复中使用这些命令（单独一行）：\n"
        f"- 列出 或 ls - 列出当前目录内容\n"
        f"- 进入 <路径> 或 cd <路径> - 切换目录\n"
        f"- 查看 <文件> 或 cat <文件> - 查看文件内容\n"
        f"- 查找 <关键词> 或 find <关键词> - 查找文件\n"
        f"- 当前路径 或 pwd - 显示当前路径\n"
        f"\n重要提示：\n"
        f"1. 当用户问'某个目录有什么文件'时，先用'cd 目录'切换，再用'ls'列出\n"
        f"2. 当用户问'查看某个文件'时，直接用'cat 文件路径'\n"
        f"3. 命令必须单独一行，不要加在句子中间\n"
        f"4. 如果路径未授权会提示，告诉用户需要授权\n"
        f"\n请使用 Markdown 格式回复。"
    )

    messages = [{"role": "system", "content": system_content}]

    history = get_history(model_key)
    for c in history:
        messages.append({"role": c["role"], "content": c["content"]})

    if user_message:
        messages.append({"role": "user", "content": user_message})

    return messages


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/models", methods=["GET"])
def list_models():
    """返回所有模型列表（不包含 API Key）"""
    models_info = []
    for key, cfg in MODELS.items():
        models_info.append({
            "key": key,
            "name": cfg.get("name", key),
            "provider": cfg.get("provider", ""),
            "api_base": cfg.get("api_base", ""),
            "model": cfg.get("model", ""),
            "api_key_masked": cfg.get("api_key", "")[:8] + "..." if cfg.get("api_key") else "",
        })
    return jsonify(models_info)


@app.route("/api/models/<model_key>", methods=["GET"])
def get_model_config(model_key):
    """获取单个模型的完整配置"""
    cfg = MODELS.get(model_key)
    if not cfg:
        return jsonify({"error": f"模型 {model_key} 不存在"}), 404
    return jsonify({
        "key": model_key,
        "name": cfg.get("name", ""),
        "provider": cfg.get("provider", ""),
        "api_key": cfg.get("api_key", ""),
        "api_base": cfg.get("api_base", ""),
        "model": cfg.get("model", ""),
        "max_tokens": cfg.get("max_tokens", 4096),
        "temperature": cfg.get("temperature", 0.7),
    })


@app.route("/api/models", methods=["POST"])
def create_model():
    """新增模型"""
    data = request.get_json()
    model_key = data.get("key", "").strip()

    if not model_key:
        return jsonify({"error": "模型 key 不能为空"}), 400
    if model_key in MODELS:
        return jsonify({"error": f"模型 {model_key} 已存在"}), 400

    cfg = {
        "name": data.get("name", model_key),
        "provider": data.get("provider", "openai"),
        "api_key": data.get("api_key", ""),
        "api_base": data.get("api_base", ""),
        "model": data.get("model", ""),
    }
    if data.get("max_tokens"):
        cfg["max_tokens"] = int(data["max_tokens"])
    if data.get("temperature") is not None:
        cfg["temperature"] = float(data["temperature"])

    MODELS[model_key] = cfg
    save_models(MODELS)
    return jsonify({"status": "ok", "key": model_key})


@app.route("/api/models/<model_key>", methods=["PUT"])
def update_model(model_key):
    """更新模型配置"""
    if model_key not in MODELS:
        return jsonify({"error": f"模型 {model_key} 不存在"}), 404

    data = request.get_json()
    new_key = data.get("key", model_key).strip()

    cfg = MODELS[model_key]
    if "name" in data:
        cfg["name"] = data["name"]
    if "provider" in data:
        cfg["provider"] = data["provider"]
    if "api_key" in data:
        cfg["api_key"] = data["api_key"]
    if "api_base" in data:
        cfg["api_base"] = data["api_base"]
    if "model" in data:
        cfg["model"] = data["model"]
    if data.get("max_tokens") is not None:
        cfg["max_tokens"] = int(data["max_tokens"])
    if data.get("temperature") is not None:
        cfg["temperature"] = float(data["temperature"])

    if new_key != model_key:
        if new_key in MODELS and new_key != model_key:
            return jsonify({"error": f"模型 {new_key} 已存在"}), 400
        if model_key in conversations:
            conversations[new_key] = conversations.pop(model_key)
        del MODELS[model_key]
        MODELS[new_key] = cfg

    save_models(MODELS)
    return jsonify({"status": "ok", "key": new_key})


@app.route("/api/models/<model_key>", methods=["DELETE"])
def delete_model(model_key):
    """删除模型"""
    if model_key not in MODELS:
        return jsonify({"error": f"模型 {model_key} 不存在"}), 404

    del MODELS[model_key]
    if model_key in conversations:
        del conversations[model_key]

    save_models(MODELS)
    return jsonify({"status": "ok"})


@app.route("/api/prompts")
def list_prompts():
    return jsonify(PROMPT_TEMPLATES)


@app.route("/api/current_dir")
def get_current_dir():
    """返回当前工作目录"""
    return jsonify({"path": current_work_dir})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    model_key = data.get("model", "deepseek")
    user_message = data.get("message", "")

    if model_key not in MODELS:
        return jsonify({"error": f"未知模型: {model_key}"}), 400

    # 检测文件操作命令
    file_result, is_file_cmd = handle_file_command(model_key, user_message)
    if is_file_cmd:
        def file_response():
            yield json.dumps({"content": file_result}) + "\n"
            yield json.dumps({"work_dir": current_work_dir}) + "\n"
        return Response(file_response(), mimetype="text/event-stream")

    history = get_history(model_key)

    if user_message:
        history.append({"role": "user", "content": user_message})

    try:
        client = get_client(model_key)
        if not client:
            return jsonify({"error": "模型配置错误，无法创建客户端"}), 500

        messages = build_messages(model_key, user_message)
        cfg = MODELS[model_key]

        extra_kwargs = {}
        if "max_tokens" in cfg:
            extra_kwargs["max_tokens"] = cfg["max_tokens"]
        if "temperature" in cfg:
            extra_kwargs["temperature"] = cfg["temperature"]

        response = client.chat.completions.create(
            model=cfg["model"],
            messages=messages,
            stream=True,
            **extra_kwargs,
        )

        def generate():
            full_content = ""
            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    yield json.dumps({"reasoning": delta.reasoning_content}) + "\n"
                if delta.content:
                    full_content += delta.content
                    yield json.dumps({"content": delta.content}) + "\n"

            # 保存 AI 回复
            history.append({"role": "assistant", "content": full_content})

            # 检查 AI 回复中是否包含文件命令并自动执行
            lines = full_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    cmd_result, is_cmd = handle_file_command(model_key, line)
                    if is_cmd:
                        # 找到命令，执行并返回结果
                        yield json.dumps({"cmd_result": cmd_result, "work_dir": current_work_dir}) + "\n"
                        # 将命令结果也添加到历史中
                        history.append({"role": "system", "content": f"[命令执行结果]\n{cmd_result}"})

        return Response(generate(), mimetype="text/event-stream")

    except Exception as e:
        if user_message and history:
            history.pop()
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            except:
                pass
        return jsonify({"error": error_detail}), 500


@app.route("/api/export")
def export_conversation():
    """导出所有模型的对话为 Markdown 格式"""
    if not conversations:
        return jsonify({"error": "对话为空"}), 400

    lines = ["# NIU AI 对话记录\n", f"导出时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", "---\n"]

    for model_key, history in conversations.items():
        if not history:
            continue
        model_name = MODELS.get(model_key, {}).get("name", model_key)
        lines.append(f"## 🤖 {model_name}（{model_key}）\n\n")
        for c in history:
            role_label = "🧑 用户" if c["role"] == "user" else "🤖 AI"
            lines.append(f"### {role_label}\n\n{c['content']}\n\n---\n")

    content = "\n".join(lines)
    return Response(
        content,
        mimetype="text/markdown",
        headers={"Content-Disposition": "attachment; filename=niu-ai-conversation.md"}
    )


@app.route("/api/conversation", methods=["DELETE"])
def clear_conversation():
    conversations.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, debug=True)
