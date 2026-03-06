## Hi there 👋

```
# AI 语音交互后端服务

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-blue.svg)](https://fastapi.tiangolo.com/)

## 项目简介

一个基于 FastAPI 和 WebSocket 的 AI 语音交互后端服务，支持多种大语言模型（LLM）、语音识别（ASR）和语音合成（TTS）服务，提供灵活的配置选项和丰富的扩展能力。

## 技术栈

- **框架**: FastAPI + WebSocket
- **语言**: Python 3.10+
- **依赖管理**: pip
- **配置管理**: YAML 分层配置
- **日志**: loguru
- **异步支持**: asyncio

## 核心功能

- ✅ 实时语音交互（ASR → LLM → TTS）
- ✅ 文本对话 API
- ✅ 支持多种大语言模型（智谱AI、豆包、通义千问等）
- ✅ 支持多种语音识别服务
- ✅ 支持多种语音合成服务
- ✅ 意图识别与工具调用
- ✅ 记忆管理
- ✅ 自动 API 文档（Swagger UI / ReDoc）
- ✅ 模块化设计，易于扩展

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/your-repo.git
cd your-repo

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

项目采用分层配置设计，优先读取顺序：
- `data/.config.yaml` - 用户自定义配置（**推荐**，不会被提交到版本控制）
- `config.yaml` - 默认配置模板

**创建配置文件**：

```bash
mkdir -p data
touch data/.config.yaml
```

**编辑配置文件**（`data/.config.yaml`）：

```yaml
# 核心配置示例
read_config_from_api: false

server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003

selected_module:
  LLM: ZhiPuLLM  # 选择要使用的大模型
  ASR: FunASR
  TTS: EdgeTTS

# 配置大模型API密钥
LLM:
  ZhiPuLLM:
    api_key: 你的智谱AI API密钥
```

### 3. 启动服务

```bash
python app.py
```

**服务将启动在**：
- WebSocket 服务：`ws://0.0.0.0:8000`
- HTTP API 服务：`http://0.0.0.0:8003`
- API 文档：`http://0.0.0.0:8003/docs`（Swagger UI）
- ReDoc 文档：`http://0.0.0.0:8003/redoc`

## 详细配置

### 配置文件结构

```yaml
# 读取配置方式
read_config_from_api: false

# 服务器配置
server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003

# 模块选择
selected_module:
  VAD: SileroVAD      # 语音活动检测
  ASR: FunASR         # 语音识别
  LLM: ZhiPuLLM       # 大语言模型
  VLLM: ChatGLMVLLM   # 视觉语言模型
  TTS: EdgeTTS        # 语音合成
  Memory: nomem       # 记忆模块
  Intent: function_call  # 意图识别

# 大模型配置
LLM:
  ZhiPuLLM:
    type: openai
    model_name: glm-4-flash
    url: https://open.bigmodel.cn/api/paas/v4/
    api_key: 你的智谱AI API密钥

  DoubaoLLM:
    type: openai
    base_url: https://ark.cn-beijing.volces.com/api/v3
    model_name: doubao-1-5-pro-32k-250115
    api_key: 你的豆包AI API密钥

# 语音识别配置
ASR:
  FunASR:
    type: fun_local
    model_dir: models/SenseVoiceSmall
    output_dir: tmp/

# 语音合成配置
TTS:
  EdgeTTS:
    type: edge
    voice: zh-CN-XiaoxiaoNeural
    output_dir: tmp/

# 日志配置
log:
  log_level: INFO
  log_dir: tmp
  log_file: "server.log"
```

### 支持的大模型

| 模型名称 | 配置节点 | API密钥位置 |
|---------|---------|------------|
| 智谱AI | ZhiPuLLM | LLM.ZhiPuLLM.api_key |
| 豆包AI | DoubaoLLM | LLM.DoubaoLLM.api_key |
| 通义千问 | AliLLM | LLM.AliLLM.api_key |
| DeepSeek | DeepSeekLLM | LLM.DeepSeekLLM.api_key |
| OpenAI GPT | OpenAILLM | LLM.OpenAILLM.api_key |
| Google Gemini | GeminiLLM | LLM.GeminiLLM.api_key |
| Ollama（本地） | OllamaLLM | 无需API密钥 |

## API 文档

### WebSocket 接口

- **地址**: `ws://{ip}:{port}/xiaozhi/v1/`
- **用途**: 实时语音交互

### HTTP API

| 接口路径 | 方法 | 用途 |
|---------|------|------|
| `/api/chat/text` | POST | 文本对话 |
| `/api/chat/voice` | POST | 语音对话 |
| `/docs` | GET | Swagger UI 文档 |
| `/redoc` | GET | ReDoc 文档 |

### 文本对话示例

```bash
curl -X POST http://localhost:8003/api/chat/text \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，介绍一下你自己"}'
```

## 目录结构

```
.
├── config/               # 配置相关
│   ├── config_loader.py  # 配置加载器
│   ├── logger.py         # 日志配置
│   └── settings.py       # 全局设置
├── core/                 # 核心代码
│   ├── fastapi_server.py # FastAPI 服务器
│   ├── websocket_server.py # WebSocket 服务器
│   ├── auth.py           # 认证管理
│   ├── handle/           # 请求处理器
│   ├── providers/        # 模型提供商
│   │   ├── asr/          # 语音识别
│   │   ├── llm/          # 大语言模型
│   │   └── tts/          # 语音合成
│   └── utils/            # 工具函数
├── data/                 # 用户数据目录
│   └── .config.yaml      # 用户配置文件（忽略提交）
├── models/               # 模型文件目录
├── plugins_func/         # 插件功能
├── app.py                # 主入口文件
├── config.yaml           # 默认配置模板
├── requirements.txt      # 依赖列表
└── README.md             # 项目说明文档
```

## 部署

### 开发环境

```bash
python app.py
```

### 生产环境（推荐使用 Docker）

**Dockerfile 示例**：

```
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8003

CMD ["python", "app.py"]
```

**Docker Compose 示例**：

```
version: '3'
services:
  ai-backend:
    build: .
    ports:
      - "8000:8000"
      - "8003:8003"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./tmp:/app/tmp
    restart: unless-stopped
```

## 扩展开发

### 添加新的大模型

1. **创建模型适配器**：
   ```bash
   mkdir -p core/providers/llm/your_model
   touch core/providers/llm/your_model/your_model.py
   ```

2. **实现模型适配器**：
   ```python
   from core.providers.llm.base import BaseLLM

   class YourModel(BaseLLM):
       def __init__(self, config):
           super().__init__(config)
           self.api_key = config.get("api_key")
           # 初始化模型客户端
       
       async def generate(self, prompt, **kwargs):
           # 实现生成逻辑
           pass
   ```

3. **在配置文件中添加模型配置**

## 日志管理

- **日志文件**: `tmp/server.log`
- **日志级别**: 可在配置文件中设置（INFO / DEBUG）
- **日志格式**: 包含时间、模块、级别、标签和消息

## 常见问题

### Q: 如何选择和配置大模型？

A: 首先在 `selected_module.LLM` 中选择要使用的模型，然后在对应模型的配置节点中填写API密钥。例如：

```
selected_module:
  LLM: DoubaoLLM  # 选择豆包AI

LLM:
  DoubaoLLM:
    api_key: 你的豆包AI API密钥  # 配置API密钥
```

### Q: 如何查看API文档？

A: 启动服务后，访问 `http://localhost:8003/docs`（Swagger UI）或 `http://localhost:8003/redoc`（ReDoc）。

### Q: 如何修改日志级别？

A: 在配置文件中修改 `log.log_level` 的值，可选值：INFO、DEBUG。

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目链接: [https://github.com/yourusername/your-repo](https://github.com/yourusername/your-repo)
- 问题反馈: [https://github.com/yourusername/your-repo/issues](https://github.com/yourusername/your-repo/issues)

## 致谢

感谢所有为本项目做出贡献的开发者和社区成员！