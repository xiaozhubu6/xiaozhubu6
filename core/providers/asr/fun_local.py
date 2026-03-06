import os
import io
import sys
import time
import shutil
import psutil
import asyncio

from funasr import AutoModel
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.utils import lang_tag_filter
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

MAX_RETRIES = 2
RETRY_DELAY = 1  # 重试延迟（秒）


# 捕获标准输出
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # 将捕获到的内容通过 logger 输出
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        
        # 内存检测，要求大于2G
        min_mem_bytes = 2 * 1024 * 1024 * 1024
        total_mem = psutil.virtual_memory().total
        if total_mem < min_mem_bytes:
            logger.bind(tag=TAG).error(f"可用内存不足2G，当前仅有 {total_mem / (1024*1024):.2f} MB，可能无法启动FunASR")
        
        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")  # 修正配置键名
        self.delete_audio_file = delete_audio_file

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="hf",
                # device="cuda:0",  # 启用GPU加速
            )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus", artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                import wave
                import io
                
                # 准备输入数据
                input_data = b""
                
                if artifacts is not None and artifacts.pcm_bytes:
                    # 如果有artifacts，优先使用artifacts中的pcm_bytes
                    input_data = artifacts.pcm_bytes
                    logger.bind(tag=TAG).info(f"使用artifacts中的PCM数据，大小: {len(input_data)}字节")
                else:
                    # 如果没有artifacts，从opus_data中提取PCM数据
                    logger.bind(tag=TAG).info(f"处理音频格式: {audio_format}")
                    
                    if audio_format == "wav":
                        # 解析WAV文件，提取PCM数据
                        for wav_file in opus_data:
                            if len(wav_file) < 12:
                                logger.bind(tag=TAG).warning(f"WAV文件太小，无法解析: {len(wav_file)}字节")
                                continue
                                
                            # 检查是否为WAV格式
                            is_wav = (wav_file.startswith(b'RIFF') and wav_file[8:12] == b'WAVE') or \
                                    (wav_file.startswith(b'FFIR') and wav_file[8:12] == b'EVAW')
                                    
                            if not is_wav:
                                logger.bind(tag=TAG).warning(f"不是有效的WAV文件，文件头: {wav_file[:12]}")
                                continue
                                
                            try:
                                with io.BytesIO(wav_file) as f:
                                    with wave.open(f, 'rb') as wf:
                                        # 获取WAV文件信息
                                        nchannels = wf.getnchannels()
                                        sampwidth = wf.getsampwidth()
                                        framerate = wf.getframerate()
                                        nframes = wf.getnframes()
                                        
                                        logger.bind(tag=TAG).info(f"解析WAV文件: 通道数={nchannels}, 采样宽度={sampwidth}, 采样率={framerate}, 帧数={nframes}")
                                        
                                        # 读取PCM数据
                                        wav_pcm_data = wf.readframes(nframes)
                                        input_data += wav_pcm_data
                                        logger.bind(tag=TAG).info(f"从WAV文件中提取PCM数据，大小: {len(wav_pcm_data)}字节")
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"解析WAV文件失败: {e}")
                                continue
                    elif audio_format == "pcm":
                        # 直接使用PCM数据
                        for pcm_frame in opus_data:
                            input_data += pcm_frame
                        logger.bind(tag=TAG).info(f"合并PCM数据，总大小: {len(input_data)}字节")
                    else:
                        # 其他格式，尝试直接使用
                        for data in opus_data:
                            input_data += data
                        logger.bind(tag=TAG).info(f"使用原始音频数据，大小: {len(input_data)}字节")
                
                # 检查输入数据是否为空
                if not input_data:
                    logger.bind(tag=TAG).warning("没有有效的音频数据可以识别")
                    return "", None
                
                # 语音识别 - 使用线程池避免阻塞事件循环
                start_time = time.time()
                result = await asyncio.to_thread(
                    self.model.generate,
                    input=input_data,
                    cache={},
                    language="auto",
                    use_itn=True,
                    batch_size_s=60,
                )
                
                # 处理识别结果
                if result and len(result) > 0 and "text" in result[0]:
                    text_result = lang_tag_filter(result[0]["text"])
                    logger.bind(tag=TAG).debug(
                        f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text_result['content']}"
                    )
                    
                    # 返回结果
                    file_path = artifacts.file_path if artifacts else None
                    return text_result, file_path
                else:
                    logger.bind(tag=TAG).warning(f"ASR返回空结果: {result}")
                    return "", None
                    

            except OSError as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.bind(tag=TAG).error(
                        f"语音识别失败（已重试{retry_count}次）: {e}", exc_info=True
                    )
                    return "", None
                logger.bind(tag=TAG).warning(
                    f"语音识别失败，正在重试（{retry_count}/{MAX_RETRIES}）: {e}"
                )
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
                return "", None
