import asyncio
import base64
import io
import os
import time
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from config.logger import setup_logging
from core.utils.modules_initialize import initialize_tts, initialize_asr
from core.utils import llm
from core.utils.prompt_manager import PromptManager
from core.utils.util import get_local_ip

# 创建FastAPI应用
app = FastAPI(
    title="AI语音聊天助手API",
    description="提供语音和文本聊天功能",
    version="1.0.0"
)

TAG = __name__
logger = setup_logging()

# 全局变量
llm_instance = None
tts_instance = None
asr_instance = None
system_prompt = "你是一个智能机器人，友好地回答用户的问题。"
welcome_prompt = "你好，有什么可以帮助你的吗？"

# 读取prompt.txt文件内容作为系统提示词和欢迎消息
def load_prompt_file():
    """加载提示词文件"""
    global system_prompt, welcome_prompt
    
    prompt_file_path = "prompt.txt"
    default_system_prompt = "你是一个智能机器人，友好地回答用户的问题。"
    default_welcome_prompt = "你好，有什么可以帮助你的吗？"
    
    if os.path.exists(prompt_file_path):
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
            
            # 使用文件内容作为系统提示词
            system_prompt = file_content
            
            # 如果文件内容是简单的问候语，直接使用它作为欢迎消息
            # 否则使用默认欢迎消息
            if len(file_content) < 100:
                welcome_prompt = file_content
            else:
                welcome_prompt = default_welcome_prompt
                
            logger.bind(tag=TAG).info(f"从prompt.txt文件加载系统提示词")
            logger.bind(tag=TAG).debug(f"系统提示词内容: {system_prompt[:100]}...")
            logger.bind(tag=TAG).info(f"欢迎消息: {welcome_prompt}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"读取prompt.txt文件失败: {e}")
            system_prompt = default_system_prompt
            welcome_prompt = default_welcome_prompt
    else:
        # 如果文件不存在，使用默认值
        system_prompt = default_system_prompt
        welcome_prompt = default_welcome_prompt
        logger.bind(tag=TAG).info(f"使用默认系统提示词和欢迎消息")

async def initialize_providers(config):
    """初始化服务提供者"""
    global llm_instance, tts_instance, asr_instance
    
    try:
        # 初始化LLM
        select_llm_module = config["selected_module"]["LLM"]
        llm_type = (
            select_llm_module
            if "type" not in config["LLM"][select_llm_module]
            else config["LLM"][select_llm_module]["type"]
        )
        llm_instance = llm.create_instance(
            llm_type,
            config["LLM"][select_llm_module],
        )
        logger.bind(tag=TAG).info("LLM初始化成功")
        
        # 初始化TTS
        tts_instance = initialize_tts(config)
        logger.bind(tag=TAG).info("TTS初始化成功")
        
        # 初始化ASR
        asr_instance = initialize_asr(config)
        logger.bind(tag=TAG).info("ASR初始化成功")
        
        return True
    except Exception as e:
        logger.bind(tag=TAG).error(f"服务提供者初始化失败: {e}")
        import traceback
        logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
        return False

from pydantic import BaseModel

# 定义请求模型
class TextChatRequest(BaseModel):
    message: str

# 文本消息交互
@app.post("/api/chat/text")
async def handle_text_chat(request: TextChatRequest):
    """处理文本消息交互"""
    try:
        message = request.message
        logger.bind(tag=TAG).info(f"收到文本消息: '{message}'")
        
        # 如果消息为空，返回错误，要求非空文本
        if not message:
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": "消息不能为空",
                    "data": None
                }
            )
        
        # 调用LLM生成回复，使用从prompt.txt加载的系统提示词
        response_text = llm_instance.response_no_stream(
            system_prompt=system_prompt,
            user_prompt=message
        )
        
        logger.bind(tag=TAG).info(f"LLM文本回复: {response_text}")
        
        # 调用TTS生成语音
        try:
            audio_data = await tts_instance.text_to_speak(response_text, None)
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS生成语音失败: {e}")
            audio_data = b""
        
        # 将语音数据转换为Base64编码
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # 返回响应
        return {
            "code": 200,
            "message": "success",
            "data": {
                "text": response_text,
                "audioBase64": audio_base64
            }
        }
    except Exception as e:
        logger.bind(tag=TAG).error(f"文本消息处理失败: {e}")
        import traceback
        logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None
            }
        )

# 语音消息交互
@app.post("/api/chat/voice")
async def handle_voice_chat(
    audio: UploadFile = File(...),
    text: str = Form("")
):
    """处理语音消息交互"""
    try:
        # 读取音频数据
        audio_data = await audio.read()
        frontend_text = text
        
        logger.bind(tag=TAG).info(f"收到语音文件，大小: {len(audio_data)}字节，类型: {audio.filename}")
        logger.bind(tag=TAG).info(f"从请求中获取到前端识别的文本: '{frontend_text}'")
        
        # 确保frontend_text是字符串类型
        if frontend_text is None:
            frontend_text = ""
        
        # 调用ASR将语音转换为文本
        asr_result = ""
        
        # 确定最终使用的文本
        # 优先使用前端传递的文本，因为前端使用Web Speech API进行了实时识别
        if frontend_text and frontend_text.strip() and frontend_text != "语音消息" and frontend_text != "无法识别语音":
            message = frontend_text
            logger.bind(tag=TAG).info(f"使用前端Web Speech API识别的文本: {message}")
        else:
            # 如果前端没有提供有效的文本，调用后端ASR进行识别
            try:
                # 调用后端ASR识别音频数据
                # 检查是否为WAV格式
                is_wav = False
                if len(audio_data) >= 12:  # WAV文件头至少12字节
                    # 打印文件头信息，便于调试
                    logger.bind(tag=TAG).info(f"音频文件头前12字节: {audio_data[:12]}")
                    # 检查RIFF标识和WAVE标识
                    # 考虑字节序问题，检查正常顺序和倒序
                    is_wav = (audio_data.startswith(b'RIFF') and audio_data[8:12] == b'WAVE') or \
                            (audio_data.startswith(b'FFIR') and audio_data[8:12] == b'EVAW')
                
                # 调用ASR识别，传递正确的音频格式
                if is_wav:
                    logger.bind(tag=TAG).info(f"收到WAV格式音频，大小: {len(audio_data)}字节")
                    # 对于WAV格式，直接调用ASR识别
                    asr_result, _ = await asr_instance.speech_to_text([audio_data], str(time.time()), audio_format="wav")
                else:
                    # 非WAV格式，尝试使用PCM格式
                    logger.bind(tag=TAG).info(f"收到非WAV格式音频，大小: {len(audio_data)}字节")
                    asr_result, _ = await asr_instance.speech_to_text([audio_data], str(time.time()), audio_format="pcm")
                
                # 处理ASR识别结果
                if asr_result:
                    if isinstance(asr_result, dict):
                        # FunASR返回的dict格式，提取content字段
                        message = asr_result.get("content", "")
                    else:
                        # 其他ASR返回的纯文本
                        message = asr_result
                    
                    logger.bind(tag=TAG).info(f"使用后端ASR识别的文本: {message}")
                else:
                    # 如果ASR也无法识别，使用"无法识别语音"作为默认
                    message = "无法识别语音"
                    logger.bind(tag=TAG).info(f"前端和后端ASR都没有提供有效文本，使用默认文本: {message}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"后端ASR识别失败: {e}")
                # ASR识别失败时，使用"无法识别语音"作为默认
                message = "无法识别语音"
        
        logger.bind(tag=TAG).info(f"语音转文本最终结果: {message}")
        
        # 调用LLM生成回复，使用从prompt.txt加载的系统提示词
        response_text = llm_instance.response_no_stream(
            system_prompt=system_prompt,
            user_prompt=message
        )
        
        logger.bind(tag=TAG).info(f"LLM语音回复: {response_text}")
        
        # 调用TTS生成语音
        try:
            audio_bytes = await tts_instance.text_to_speak(response_text, None)
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS生成语音失败: {e}")
            audio_bytes = b""
        
        # 将语音数据转换为Base64编码
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # 返回响应，包含原始语音识别结果
        return {
            "code": 200,
            "message": "success",
            "data": {
                "text": response_text,
                "audioBase64": audio_base64,
                "recognizedText": message  # 新增：返回语音识别结果
            }
        }
    except Exception as e:
        logger.bind(tag=TAG).error(f"语音消息处理失败: {e}")
        import traceback
        logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None
            }
        )

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "ok",
            "timestamp": time.time()
        }
    }

class FastAPIServer:
    def __init__(self, config: dict):
        self.config = config
        # 加载提示词文件
        load_prompt_file()
    
    async def start(self):
        """启动FastAPI服务器"""
        try:
            # 初始化服务提供者
            if not await initialize_providers(self.config):
                logger.bind(tag=TAG).error("服务提供者初始化失败，无法启动FastAPI服务器")
                return
            
            # 获取服务器配置
            server_config = self.config["server"]
            host = server_config.get("ip", "0.0.0.0")
            port = int(server_config.get("http_port", 8003))
            
            logger.bind(tag=TAG).info(f"FastAPI服务器已启动，监听地址: http://{host}:{port}")
            logger.bind(tag=TAG).info(f"文本消息接口: http://{get_local_ip()}:{port}/api/chat/text")
            logger.bind(tag=TAG).info(f"语音消息接口: http://{get_local_ip()}:{port}/api/chat/voice")
            logger.bind(tag=TAG).info(f"健康检查接口: http://{get_local_ip()}:{port}/health")
            logger.bind(tag=TAG).info(f"API文档: http://{get_local_ip()}:{port}/docs")
            logger.bind(tag=TAG).info(f"API文档(ReDoc): http://{get_local_ip()}:{port}/redoc")
            
            # 启动服务器
            import uvicorn
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                reload=False,
                loop="asyncio",
                log_level="info"
            )
            server = uvicorn.Server(config)
            # 使用现有事件循环运行服务器
            await server.serve()
        except Exception as e:
            logger.bind(tag=TAG).error(f"FastAPI服务器启动失败: {e}")
            import traceback
            logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
            raise
