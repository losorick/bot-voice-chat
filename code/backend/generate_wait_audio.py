#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成等待语音音频"""

from dotenv import load_dotenv
load_dotenv()

from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
from dashscope.audio.tts_v2.speech_synthesizer import ResultCallback
import os
import time

API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
if not API_KEY:
    print("❌ 错误: 未设置 DASHSCOPE_API_KEY")
    exit(1)

OUTPUT_DIR = os.path.expanduser("~/Documents/项目记录/bot语音沟通/wait_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 短语列表
phrases = [
    "收到好的", "好的收到", "明白收到", "我知道了", "收到明白",
    "没问题", "好的好的", "OK收到", "收到啦", "了解了解",
    "马上就好", "稍等一下", "等一下哈", "很快就好", "请稍等会",
    "马上到", "等会啊", "很快马上", "请等一下", "马上处理",
    "已经完成", "搞定搞定", "办好了", "完成了", "已经搞定",
    "OK完成了", "没问题哈", "已经弄好", "搞定了哈", "处理完毕",
    "好的好的", "没问题", "好的收到", "好的明白", "好的好的",
    "没问题OK", "好的知道了", "好的马上去", "好的明白啦", "好的好的呀",
    "马上马上", "立刻就去", "马上处理", "立即执行", "马上就好",
    "立刻马上", "马上搞定", "立即行动", "马上去办", "马上完成",
    "收到收到", "好的收到", "收到明白", "收到啦收到", "收到没问题",
    "收到马上去", "收到明白啦", "收到OK啦", "收到好的呀", "收到马上办"
]

def sanitize_filename(text):
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(char, '')
    return text

class AudioCallback(ResultCallback):
    def __init__(self):
        self.audio_data = bytearray()
    
    def on_data(self, data: bytes) -> None:
        self.audio_data.extend(data)

def generate_audio(text, output_path):
    """生成单个音频"""
    callback = AudioCallback()
    synthesizer = SpeechSynthesizer(
        model='cosyvoice-v3-flash',
        voice='longhuhu_v3',
        format=AudioFormat.PCM_22050HZ_MONO_16BIT,
        callback=callback
    )
    
    synthesizer.streaming_call(text)
    synthesizer.streaming_complete()
    
    if callback.audio_data:
        # 转换为 WAV 格式
        import wave
        import io
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(callback.audio_data)
        
        with open(output_path, 'wb') as f:
            f.write(wav_buffer.getvalue())
        return True
    return False

def main():
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"📝 短语数量: {len(phrases)}\n")
    
    success = 0
    failed = 0
    
    for i, phrase in enumerate(phrases, 1):
        filename = sanitize_filename(phrase)
        output_path = os.path.join(OUTPUT_DIR, f"{filename}.wav")
        
        print(f"[{i}/{len(phrases)}] 生成: {phrase}")
        
        if generate_audio(phrase, output_path):
            success += 1
            print("  ✅ 成功")
        else:
            failed += 1
            print("  ❌ 失败")
        
        time.sleep(0.3)
    
    print()
    print("=" * 50)
    print(f"✅ 成功: {success} 个")
    if failed > 0:
        print(f"❌ 失败: {failed} 个")
    print(f"📁 位置: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
