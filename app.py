import json
import os
import shutil
import re
import difflib
import ast
import sqlite3
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response
from openai import OpenAI
from config import MODELS, save_models

# 文件操作支持
ALLOWED_ROOT = os.path.expanduser("~")
current_work_dir = "/Users/niuzilin/VSCodeProjects/Test01"

# 权限管理：存储用户授权的路径
authorized_paths = {ALLOWED_ROOT}  # 默认允许用户主目录

# 项目结构缓存
project_structure = {}
recent_modifications = []

def scan_project_structure(root_dir, max_depth=3):
    """扫描项目结构，提取文件信息"""
    structure = {
        "files": [],
        "functions": {},
        "classes": {},
        "imports": {}
    }

    ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.env'}

    try:
        for root, dirs, files in os.walk(root_dir):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in ignore_patterns]

            depth = root.replace(root_dir, '').count(os.sep)
            if depth > max_depth:
                continue

            for file in files:
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_dir)

                structure["files"].append({
                    "path": rel_path,
                    "name": file,
                    "size": os.path.getsize(file_path),
                    "ext": os.path.splitext(file)[1]
                })

                # 解析 Python 文件
                if file.endswith('.py'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read())

                        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

                        if functions:
                            structure["functions"][rel_path] = functions
                        if classes:
                            structure["classes"][rel_path] = classes
                    except:
                        pass
    except Exception as e:
        print(f"扫描项目失败: {e}")

    return structure

def get_project_context():
    """获取项目上下文信息"""
    global project_structure

    if not project_structure:
        project_structure = scan_project_structure(current_work_dir)

    # 生成简洁的项目摘要
    total_files = len(project_structure["files"])
    py_files = len([f for f in project_structure["files"] if f["ext"] == ".py"])

    context = f"项目文件总数: {total_files}, Python文件: {py_files}\n"

    # 列出主要文件
    main_files = [f["path"] for f in project_structure["files"][:20]]
    context += "主要文件:\n" + "\n".join(f"  - {f}" for f in main_files)

    remaining = len(project_structure["files"]) - 20
    if remaining > 0:
        context += f"\n  ... 还有 {remaining} 个文件"

    return context

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

    # 写入文件: 写入 <file> <content>
    m = re.match(r'^(写入|write)\s+(.+?)\s+(.+)$', msg, re.DOTALL)
    if m:
        filename = m.group(2).strip()
        content = m.group(3).strip()
        target_path = safe_path(filename)
        if not is_path_authorized(os.path.dirname(target_path)):
            return request_path_authorization(target_path), True
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            recent_modifications.append({"action": "write", "path": target_path})
            return f"✅ 已写入文件: {target_path}", True
        except Exception as e:
            return f"❌ 写入失败: {str(e)}", True

    # 创建文件: 创建 <file>
    m = re.match(r'^(创建|create|touch)\s+(.+)$', msg)
    if m:
        filename = m.group(2).strip()
        target_path = safe_path(filename)
        if not is_path_authorized(os.path.dirname(target_path)):
            return request_path_authorization(target_path), True
        try:
            Path(target_path).touch()
            recent_modifications.append({"action": "create", "path": target_path})
            return f"✅ 已创建文件: {target_path}", True
        except Exception as e:
            return f"❌ 创建失败: {str(e)}", True

    # 删除文件: 删除 <file>
    m = re.match(r'^(删除|delete|rm)\s+(.+)$', msg)
    if m:
        filename = m.group(2).strip()
        target_path = safe_path(filename)
        if not is_path_authorized(target_path):
            return request_path_authorization(target_path), True
        try:
            if os.path.isfile(target_path):
                os.remove(target_path)
                recent_modifications.append({"action": "delete", "path": target_path})
                return f"✅ 已删除文件: {target_path}", True
            else:
                return f"❌ 文件不存在: {target_path}", True
        except Exception as e:
            return f"❌ 删除失败: {str(e)}", True

    # 查看项目结构: 项目结构 或 tree
    if msg in ('项目结构', 'tree', 'structure'):
        if not is_path_authorized(current_work_dir):
            return request_path_authorization(current_work_dir), True
        global project_structure
        project_structure = scan_project_structure(current_work_dir)
        files_list = "\n".join(f"  - {f['path']}" for f in project_structure["files"][:50])
        if len(project_structure["files"]) > 50:
            files_list += f"\n  ... 还有 {len(project_structure['files']) - 50} 个文件"
        return f"📂 项目结构 ({len(project_structure['files'])} 个文件):\n{files_list}", True

    # 不是文件命令
    return None, False


app = Flask(__name__)

# 提示词模板
PROMPT_TEMPLATES = [
    {"name": "代码审查", "prompt": "请审查以下代码，指出潜在问题和改进建议"},
    {"name": "代码解释", "prompt": "请详细解释以下代码的功能和实现逻辑"},
    {"name": "Bug 修复", "prompt": "以下代码出现了问题，请帮我分析并修复"},
    {"name": "性能优化", "prompt": "请分析以下代码的性能问题，并提供优化建议"},
    {"name": "重构建议", "prompt": "请对以下代码提出重构建议，使其更易维护"},
]

# SQLite 数据库初始化
DB_PATH = "chat_sessions.db"

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  model_key TEXT NOT NULL,
                  role TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# 当前会话ID
current_session_id = "default"

def get_session_conversations():
    """获取当前会话的对话历史（从数据库）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT model_key, role, content FROM messages
                 WHERE session_id = ? ORDER BY id ASC''', (current_session_id,))
    rows = c.fetchall()
    conn.close()

    # 按模型分组
    conversations = {}
    for model_key, role, content in rows:
        if model_key not in conversations:
            conversations[model_key] = []
        conversations[model_key].append({"role": role, "content": content})

    return conversations

def get_history(model_key):
    """获取指定模型在当前会话的对话历史"""
    convs = get_session_conversations()
    return convs.get(model_key, [])

def save_message(session_id, model_key, role, content):
    """保存消息到数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO messages (session_id, model_key, role, content)
                 VALUES (?, ?, ?, ?)''', (session_id, model_key, role, content))
    conn.commit()
    conn.close()


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

    # 获取项目上下文
    project_ctx = get_project_context()

    # 最近修改
    recent_mods = ""
    if recent_modifications:
        recent_mods = "\n最近修改的文件:\n" + "\n".join(
            f"  - {m['action']}: {m['path']}"
            for m in recent_modifications[-5:]
        )

    system_content = (
        f"你是一个有用的AI编程助手，具备完整的文件系统访问和编辑能力。"
        f"你当前正在被调用的模型是：{model_display_name}（API模型名：{model_api_name}）。"
        f"\n\n## 项目信息\n"
        f"当前工作目录：{current_work_dir}\n"
        f"{project_ctx}"
        f"{recent_mods}\n"
        f"\n## 文件操作能力\n"
        f"你可以直接使用以下命令操作文件（命令必须单独一行）：\n"
        f"\n查看操作：\n"
        f"- 列出 / ls - 列出当前目录内容\n"
        f"- 进入 <路径> / cd <路径> - 切换目录\n"
        f"- 查看 <文件> / cat <文件> - 查看文件内容\n"
        f"- 查找 <关键词> / find <关键词> - 查找文件\n"
        f"- 项目结构 / tree - 查看项目结构\n"
        f"- 当前路径 / pwd - 显示当前路径\n"
        f"\n编辑操作：\n"
        f"- 写入 <文件> <内容> - 创建或覆盖文件\n"
        f"- 创建 <文件> - 创建空文件\n"
        f"- 删除 <文件> - 删除文件\n"
        f"\n使用建议：\n"
        f"1. 修改代码前先用'查看'命令看原内容\n"
        f"2. 理解项目结构后再进行修改\n"
        f"3. 一次修改一个文件，确保逻辑清晰\n"
        f"4. 命令必须单独一行，不要嵌入句子中\n"
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


@app.route("/api/project/structure")
def get_project_structure():
    """返回项目结构"""
    global project_structure
    if not project_structure:
        project_structure = scan_project_structure(current_work_dir)
    return jsonify(project_structure)


@app.route("/api/file/read", methods=["POST"])
def read_file_api():
    """读取文件内容"""
    data = request.get_json()
    file_path = data.get("path", "")
    target_path = safe_path(file_path)

    if not is_path_authorized(target_path):
        return jsonify({"error": "未授权访问"}), 403

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content, "path": target_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file/write", methods=["POST"])
def write_file_api():
    """写入文件内容"""
    data = request.get_json()
    file_path = data.get("path", "")
    content = data.get("content", "")
    target_path = safe_path(file_path)

    if not is_path_authorized(os.path.dirname(target_path)):
        return jsonify({"error": "未授权访问"}), 403

    try:
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        recent_modifications.append({"action": "write", "path": target_path})
        return jsonify({"status": "ok", "path": target_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file/diff", methods=["POST"])
def file_diff_api():
    """生成文件 diff"""
    data = request.get_json()
    file_path = data.get("path", "")
    new_content = data.get("content", "")
    target_path = safe_path(file_path)

    if not is_path_authorized(target_path):
        return jsonify({"error": "未授权访问"}), 403

    try:
        # 读取原文件
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
        else:
            old_content = ""

        # 生成 diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        ))

        return jsonify({
            "diff": diff,
            "old_content": old_content,
            "new_content": new_content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """获取所有会话列表（从数据库）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT session_id, COUNT(*) as msg_count
                 FROM messages GROUP BY session_id''')
    rows = c.fetchall()
    conn.close()

    session_list = []
    session_ids = set([row[0] for row in rows])

    # 确保当前会话在列表中
    if current_session_id not in session_ids:
        session_ids.add(current_session_id)

    for sid in session_ids:
        msg_count = next((row[1] for row in rows if row[0] == sid), 0)
        session_list.append({
            "id": sid,
            "message_count": msg_count,
            "is_current": sid == current_session_id
        })

    return jsonify(session_list)


@app.route("/api/sessions/<session_id>", methods=["POST"])
def switch_session(session_id):
    """切换到指定会话"""
    global current_session_id
    current_session_id = session_id
    return jsonify({"status": "ok", "session_id": session_id})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """删除指定会话（从数据库）"""
    global current_session_id

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

    if current_session_id == session_id:
        current_session_id = "default"
    return jsonify({"status": "ok"})


@app.route("/api/sessions/current", methods=["GET"])
def get_current_session():
    """获取当前会话ID和历史"""
    return jsonify({
        "session_id": current_session_id,
        "conversations": get_session_conversations()
    })


@app.route("/api/sessions/current/clear", methods=["POST"])
def clear_current_session():
    """清空当前会话的对话历史"""
    data = request.get_json() or {}
    model_key = data.get("model")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if model_key:
        # 只清空指定模型的历史
        c.execute('DELETE FROM messages WHERE session_id = ? AND model_key = ?',
                  (current_session_id, model_key))
    else:
        # 清空整个会话
        c.execute('DELETE FROM messages WHERE session_id = ?', (current_session_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


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
        save_message(current_session_id, model_key, "user", user_message)

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

            # 保存 AI 回复到数据库
            save_message(current_session_id, model_key, "assistant", full_content)

            # 检查 AI 回复中是否包含文件命令并自动执行
            lines = full_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    cmd_result, is_cmd = handle_file_command(model_key, line)
                    if is_cmd:
                        # 找到命令，执行并返回结果
                        yield json.dumps({"cmd_result": cmd_result, "work_dir": current_work_dir}) + "\n"
                        # 将命令结果也保存到数据库
                        save_message(current_session_id, model_key, "system", f"[命令执行结果]\n{cmd_result}")

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
