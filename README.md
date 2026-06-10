# NIU AI - AI 编程助手

一个基于 Flask 的多模型 AI 编程助手，支持文件操作、项目分析、Git 集成和终端命令执行。

## 核心特性

### 🤖 AI 工具调用
- **文件操作** - 读取、写入、创建、删除文件
- **项目分析** - 自动扫描项目结构，识别函数和类
- **Git 集成** - 查看状态、diff、提交更改
- **终端执行** - 运行 Python、npm、git 等安全命令
- **Diff 预览** - 修改前显示差异对比

### 💬 多模型支持
- 同时配置多个 AI 模型（DeepSeek、Doubao 等）
- 每个模型独立对话历史
- 灵活切换不同模型

### 📊 会话管理
- 创建多个独立会话
- 每个会话保存独立对话
- 支持重命名、删除会话

### 🎨 界面功能
- 🌓 深色/浅色主题切换
- 📁 项目文件浏览器
- 🔀 Git 操作面板
- 📝 Markdown 渲染（代码高亮、表格）
- 💾 SQLite 持久化存储

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入 API Key：

```env
DEEPSEEK_API_KEY=your_api_key_here
DOUBAO_API_KEY=your_api_key_here
```

### 3. 启动服务

```bash
./start.sh
# 或
python3 app.py
```

访问 http://localhost:8088

### 4. 停止服务

```bash
./stop.sh
```

## AI 工具使用

### 文件操作

**read_file** - 读取文件
```
用户: 帮我看看 app.py 的内容
AI: [自动调用 read_file 工具]
```

**write_file** - 写入文件
```
用户: 创建一个 test.py，写入 print('hello')
AI: [自动调用 write_file 工具]
```

**preview_write_file** - 预览修改差异
```
用户: 把 demo.txt 里的 hello 改成 hi
AI: [显示 diff 预览]
    --- a/demo.txt
    +++ b/demo.txt
    @@ -1 +1 @@
    -hello world
    +hi world
```

### 项目分析

**get_project_structure** - 获取项目结构
```
用户: 这个项目有哪些文件？
AI: [扫描项目]
    项目包含 17 个文件：
    - app.py (12 functions, 2 classes)
    - config.py
    - templates/index.html
    ...
```

### Git 操作

**git_status** - 查看状态
```
用户: git status
AI: [显示当前修改]
```

**git_diff** - 查看差异
```
用户: 看看我改了什么
AI: [显示代码差异]
```

**git_commit** - 提交更改
```
用户: 提交代码，消息是"修复bug"
AI: [执行 git commit]
```

### 终端命令

**run_command** - 执行安全命令
```
用户: 安装 requests 库
AI: [执行 pip install requests]
```

支持的命令白名单：
- Python: pip, python, pytest
- Node.js: npm, yarn, node
- Git: git
- 构建工具: make, cargo, go
- 查看类: ls, cat, pwd

## 权限管理

### 授权机制
- 默认只允许访问用户主目录（`~`）
- 访问其他路径需要明确授权

### 授权命令

**授权路径**
```
授权 /Applications
```

**查看已授权路径**
```
已授权路径
```

### 使用示例

```
用户: 进入 /Applications
AI: ⚠️ 该路径需要授权访问

用户: 授权 /Applications
AI: ✅ 已授权访问

用户: 列出
AI: 📁 /Applications
    📁 Chrome.app/
    📁 Safari.app/
```

## 添加新模型

1. 点击设置图标 ⚙️
2. 点击"+ 添加新模型"
3. 填写配置：
   - **模型标识**: 唯一 ID（如 `gpt4`）
   - **显示名称**: 界面显示名称
   - **Provider**: OpenAI 兼容或 Anthropic
   - **API Key**: 模型密钥
   - **API Base**: API 端点
   - **模型名称**: API 调用名称
   - **Max Tokens**: 最大生成长度
   - **Temperature**: 生成温度（0-1）

## 项目结构

```
.
├── app.py              # Flask 主应用
├── config.py           # 模型配置管理
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html     # Web 前端界面
├── start.sh           # 启动脚本
├── stop.sh            # 停止脚本
├── chat_sessions.db   # SQLite 数据库（自动生成）
├── .env               # 环境变量（不在 git）
└── models.json        # 模型配置（不在 git）
```

## 工作原理

### AI 工具调用流程

1. 用户发送请求："帮我读取 app.py"
2. AI 识别需要调用 `read_file` 工具
3. 后端执行工具，返回文件内容
4. AI 基于内容生成回复
5. 前端显示完整结果

### 工具定义示例

```python
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取文件内容",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"]
        }
    }
}
```

### 安全机制

1. **命令白名单** - 只允许执行安全命令
2. **路径授权** - 文件访问需要显式授权
3. **危险模式检测** - 拒绝 `rm -rf /`、`sudo` 等危险操作
4. **权限检查** - 所有文件操作前验证权限

## 技术栈

- **后端**: Flask (Python)
- **数据库**: SQLite3
- **AI SDK**: OpenAI SDK（兼容多种 API）
- **前端**: 原生 HTML/CSS/JavaScript
- **Markdown**: Marked.js
- **Diff**: Python difflib

## 与商业工具对比

| 功能 | NIU AI | Claude Code | Cursor |
|------|--------|-------------|--------|
| 文件读取 | ✅ | ✅ | ✅ |
| 文件写入 | ✅ | ✅ | ✅ |
| Diff 预览 | ✅ | ✅ | ✅ |
| Git 操作 | ✅ | ✅ | ✅ |
| 终端执行 | ✅ | ✅ | ✅ |
| 项目分析 | ✅ | ✅ | ✅ |
| 多模型切换 | ✅ | ❌ | ❌ |
| IDE 集成 | ❌ | ✅ | ✅ |
| 多文件重构 | ⏳ | ✅ | ✅ |

## 开发计划

- [x] 多模型支持
- [x] 会话管理
- [x] 文件操作工具
- [x] 项目结构分析
- [x] Git 集成
- [x] 终端命令执行
- [x] Diff 预览
- [ ] 语义代码搜索
- [ ] 多文件重构
- [ ] VS Code 插件
- [ ] Docker 部署

## 安全说明

- ⚠️ API Key 存储在 `.env` 和 `models.json`，已加入 `.gitignore`
- ⚠️ 数据库 `chat_sessions.db` 包含所有对话，已加入 `.gitignore`
- ⚠️ 仅供本地使用，不要暴露到公网
- ⚠️ 终端命令仅限白名单，但仍需谨慎使用

## License

MIT

## 作者

by 牛梓霖

## 贡献

欢迎提交 Issue 和 Pull Request！
