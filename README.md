# NIU AI - 多模型 AI 聊天应用

一个基于 Flask 的多模型 AI 聊天应用，支持文件系统访问和权限管理。

## 功能特点

- 🤖 **多模型支持** - 同时使用多个 AI 模型（DeepSeek、Doubao 等），每个模型独立对话历史
- 📁 **文件系统访问** - AI 可以查看、浏览本地文件和目录
- 🔒 **权限管理** - 基于授权的安全访问机制，保护系统文件
- 💬 **流式响应** - 实时显示 AI 回复
- 📝 **Markdown 渲染** - 支持代码高亮、表格等格式
- 💾 **对话导出** - 导出为 Markdown 格式
- ⚙️ **动态配置** - Web 界面管理模型配置

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

编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DOUBAO_API_KEY=your_doubao_api_key_here
```

### 3. 启动服务

```bash
# 使用启动脚本
./start.sh

# 或直接运行
python3 app.py
```

访问 http://localhost:8088

### 4. 停止服务

```bash
./stop.sh
```

## 文件系统访问

### 权限管理

默认只允许访问用户主目录（`~`），访问其他路径需要授权：

```
授权 /Applications
授权 /System
已授权路径
```

### 可用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `进入 <路径>` / `cd <路径>` | 切换目录 | `进入 /Applications` |
| `列出` / `ls` | 列出当前目录 | `列出` |
| `查看 <文件>` / `cat <文件>` | 查看文件内容 | `查看 app.py` |
| `查找 <关键词>` / `find <关键词>` | 查找文件 | `查找 .py` |
| `当前路径` / `pwd` | 显示当前路径 | `pwd` |

### 使用示例

**用户命令方式**：
```
用户: 进入 /Applications
AI: ⚠️ 该路径需要授权访问...
用户: 授权 /Applications
AI: ✅ 已授权访问
用户: 列出
系统: 📁 Chrome.app/
      📁 Safari.app/
```

**AI 自动执行**（推荐）：
```
用户: 看看 Desktop 文件夹里有什么文件
AI: [自动执行 cd 和 ls 命令，直接显示结果]
```

## 添加新模型

1. 点击右上角设置图标 ⚙️
2. 点击"+ 添加模型"
3. 填写模型配置：
   - 模型标识：唯一 ID（如 `gpt4`）
   - 显示名称：界面显示的名称
   - API Key：模型的 API 密钥
   - API Base：API 端点地址
   - 模型名称：API 调用时使用的模型名

## 项目结构

```
.
├── app.py              # 主应用
├── config.py           # 配置管理
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html     # Web 界面
├── start.sh           # 启动脚本
├── stop.sh            # 停止脚本
├── .env               # 环境变量（不包含在 git）
└── models.json        # 模型配置（不包含在 git）
```

## 安全说明

- ⚠️ API Key 存储在 `.env` 和 `models.json` 中，已加入 `.gitignore`
- ⚠️ 文件访问默认限制在用户主目录，其他路径需要显式授权
- ⚠️ 授权是临时的，服务重启后需要重新授权
- ⚠️ macOS 系统保护（SIP）等限制仍然有效
- ⚠️ 本应用仅供本地使用，不要直接暴露到公网

## 技术栈

- **后端**: Flask (Python)
- **AI SDK**: OpenAI SDK（兼容多种 API）
- **前端**: 原生 HTML/CSS/JavaScript
- **Markdown**: Marked.js

## 开发计划

- [ ] 文件写入、复制、删除功能
- [ ] 持久化授权记录
- [ ] 用户认证系统
- [ ] 对话历史持久化
- [ ] 支持更多 AI 模型
- [ ] Docker 部署支持

## License

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
