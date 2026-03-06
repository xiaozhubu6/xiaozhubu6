# 后端服务说明文档

## 1. 项目概述

本项目是一个基于FastAPI框架的AI语音交互后端服务，支持多种大语言模型（LLM）、语音识别（ASR）和语音合成（TTS）服务。

## 2. 技术栈

- **框架**：FastAPI
- **语言**：Python 3.10+
- **通信协议**：WebSocket、HTTP
- **配置管理**：YAML分层配置

## 3. 核心功能

- 语音交互（ASR → LLM → TTS）
- 文本对话
- 意图识别与工具调用
- 记忆管理
- 多模型支持

## 4. 配置管理

### 4.1 配置文件结构

项目采用分层配置设计，优先读取顺序为：
1. `data/.config.yaml` - 用户自定义配置
2. `config.yaml` - 默认配置模板

### 4.2 大模型配置

#### 4.2.1 选择大模型

在配置文件中，通过 `selected_module.LLM` 指定要使用的大模型：

```yaml
selected_module:
  LLM: ZhiPuLLM  # 选择智谱AI模型
  # 可选值：AliLLM、DoubaoLLM、DeepSeekLLM、ChatGLMLLM、ZhiPuLLM等
```

#### 4.2.2 配置API密钥

根据选择的大模型，在对应模块中填写API密钥：

```yaml
# 智谱AI配置
LLM:
  ZhiPuLLM:
    type: openai
    model_name: glm-4-flash
    url: https://open.bigmodel.cn/api/paas/v4/
    api_key: 你的智谱AI API密钥  # 在这里填写你的API密钥
```

#### 4.2.3 支持的大模型列表

| 模型名称 | 配置节点 | API密钥位置 | 说明 |
|---------|---------|------------|------|
| 智谱AI | ZhiPuLLM | LLM.ZhiPuLLM.api_key | 支持glm-4-flash等模型 |
| 豆包AI | DoubaoLLM | LLM.DoubaoLLM.api_key | 火山引擎豆包模型 |
| 阿里通义千问 | AliLLM | LLM.AliLLM.api_key | 阿里云通义千问 |
| DeepSeek | DeepSeekLLM | LLM.DeepSeekLLM.api_key | DeepSeek大模型 |
| OpenAI | OpenAILLM | LLM.OpenAILLM.api_key | OpenAI GPT模型 |
| Gemini | GeminiLLM | LLM.GeminiLLM.api_key | 谷歌Gemini模型 |

## 5. 服务启动

### 5.1 安装依赖

```bash
pip install -r requirements.txt
```

### 5.2 启动服务

```bash
python app.py
```

服务将启动在：
- WebSocket服务：`ws://0.0.0.0:8000`
- HTTP API服务：`http://0.0.0.0:8003`
- API文档：`http://0.0.0.0:8003/docs`（Swagger UI）

## 6. API接口

### 6.1 WebSocket接口

- **地址**：`ws://{ip}:{port}/xiaozhi/v1/`
- **用途**：实时语音交互

### 6.2 HTTP接口

- **文本对话**：`POST /api/chat/text`
- **语音对话**：`POST /api/chat/voice`
- **API文档**：`GET /docs`

## 7. 大模型API配置常见问题

### 问题：是不是我用哪个大模型，就在哪个大模型填响应的api就可以了？

**回答：是的！**

具体步骤：
1. 在 `selected_module.LLM` 中选择要使用的大模型名称
2. 在对应大模型的配置节点中填写API密钥
3. 重启服务即可生效

**示例**：使用豆包AI

```yaml
# 1. 选择豆包AI
selected_module:
  LLM: DoubaoLLM

# 2. 配置豆包AI的API密钥
LLM:
  DoubaoLLM:
    type: openai
    base_url: https://ark.cn-beijing.volces.com/api/v3
    model_name: doubao-1-5-pro-32k-250115
    api_key: 你的豆包AI API密钥  # 填写你的API密钥
```

### 7.1 如何添加新的大模型？

1. 在 `core/providers/llm/` 目录下创建新的模型适配器
2. 在 `config.yaml` 中添加模型配置模板
3. 在 `selected_module.LLM` 中选择新模型
4. 在对应配置中填写API密钥

## 8. 日志管理

- 日志文件：`tmp/server.log`
- 日志级别：可在 `config.yaml` 中配置（INFO/DEBUG）
- 日志格式：包含时间、模块、级别、标签和消息

## 9. 部署建议

### 9.1 开发环境

- 直接运行 `python app.py` 启动服务
- 使用 `data/.config.yaml` 配置开发环境参数

### 9.2 生产环境

- 建议使用Docker部署
- 配置环境变量或 `data/.config.yaml` 管理敏感信息
- 启用认证机制

## 10. 安全注意事项

- **切勿**将API密钥硬编码到代码中
- **推荐**使用 `data/.config.yaml` 存储敏感信息
- 定期轮换API密钥
- 生产环境中启用认证和HTTPS

## 11. 常见问题排查

### 11.1 模型调用失败

- 检查API密钥是否正确
- 检查网络连接是否正常
- 查看日志文件 `tmp/server.log` 获取详细错误信息

### 11.2 服务无法启动

- 检查端口是否被占用
- 检查依赖是否安装完整
- 查看控制台输出的错误信息

