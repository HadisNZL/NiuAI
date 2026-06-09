# NIU AI - 多模型 AI 聊天应用

一个基于 Flask 的多模型 AI 聊天应用，支持会话管理、深色模式和持久化存储。

## 功能特点

- 🤖 **多模型支持** - 同时使用多个 AI 模型（DeepSeek、Doubao 等），每个模型独立对话历史
- 💬 **会话管理** - 创建多个会话，独立管理不同对话
- 🌓 **深色模式** - 支持浅色/深色主题切换，自动保存偏好
- 💾 **持久化存储** - SQLite 数据库保存所有对话，重启不丢失
- 📝 **Markdown 渲染** - 支持代码高亮、表格等格式
- 🎯 **快捷提示词** - 内置常用提示词模板
- 📤 **对话导出** - 导出为 Markdown 格式
- ⚙️ **动态配置** - Web 界面管理模型配置
- 💨 **流式响应** - 实时显示 AI 回复

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

## 核心功能

### 会话管理

- 点击 💬 按钮打开会话管理
- 创建多个独立会话，每个会话保存独立的对话历史
- 切换会话时自动恢复历史消息
- 删除不需要的会话

### 深色模式

- 点击 🌓 按钮切换浅色/深色主题
- 主题偏好自动保存到浏览器
- 下次访问自动恢复上次选择的主题

### 快捷提示词

在输入框上方选择常用提示词：
- 代码审查
- 代码解释
- Bug 修复
- 性能优化
- 重构建议

## 添加新模型

1. 点击右上角设置图标 ⚙️
2. 点击"+ 添加新模型"
3. 填写模型配置：
   - **模型标识**：唯一 ID（如 `gpt4`）
   - **显示名称**：界面显示的名称
   - **Provider**：选择 OpenAI 兼容或 Anthropic
   - **API Key**：模型的 API 密钥
   - **API Base**：API 端点地址
   - **模型名称**：API 调用时使用的模型名
   - **Max Tokens**：最大生成长度
   - **Temperature**：生成温度（0-1）

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
├── chat_sessions.db   # SQLite 数据库（自动生成）
├── .env               # 环境变量（不包含在 git）
└── models.json        # 模型配置（不包含在 git）
```

## 数据持久化

所有对话保存在 `chat_sessions.db` SQLite 数据库中：
- 每条消息包含：会话ID、模型、角色、内容、时间戳
- 支持多会话、多模型独立存储
- 服务重启后数据不丢失

## 安全说明

- ⚠️ API Key 存储在 `.env` 和 `models.json` 中，已加入 `.gitignore`
- ⚠️ 数据库文件 `chat_sessions.db` 包含所有对话，已加入 `.gitignore`
- ⚠️ 本应用仅供本地使用，不要直接暴露到公网

## 技术栈

- **后端**: Flask (Python)
- **数据库**: SQLite3
- **AI SDK**: OpenAI SDK（兼容多种 API）
- **前端**: 原生 HTML/CSS/JavaScript
- **Markdown**: Marked.js

## 开发计划

- [x] 多模型支持
- [x] 会话管理
- [x] 深色模式
- [x] 对话持久化（SQLite）
- [x] 快捷提示词
- [ ] 对话搜索功能
- [ ] 导出为 PDF
- [ ] 用户认证系统
- [ ] Docker 部署支持

## License

MIT

## 作者

by 牛梓霖

## 贡献

欢迎提交 Issue 和 Pull Request！
