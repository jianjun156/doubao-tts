#!/usr/bin/env python3
"""
豆包语音合成脚本 (Doubao TTS - Unidirectional Streaming HTTP V3)

通过火山引擎豆包语音合成大模型 API，将文本合成为语音音频文件。
支持声音复刻音色（S_ 开头）和官方预置音色。

使用方法:
    export DOUBAO_APP_ID="your_app_id"
    export DOUBAO_ACCESS_KEY="your_access_key"
    python3 tts_synthesize.py --text "你好世界" --speaker "S_9W2ToNVW1" --output output.mp3
"""

import argparse
import base64
import json
import os
import sys
import uuid

try:
    import requests
except ImportError:
    print("错误: 需要安装 requests 库。请运行: pip install requests --break-system-packages")
    sys.exit(1)


API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

# 音色类型到资源 ID 的映射
RESOURCE_ID_MAP = {
    "icl-1.0": "seed-icl-1.0",
    "icl-1.0-concurr": "seed-icl-1.0-concurr",
    "icl-2.0": "seed-icl-2.0",
    "tts-1.0": "seed-tts-1.0",
    "tts-1.0-concurr": "seed-tts-1.0-concurr",
    "tts-2.0": "seed-tts-2.0",
}

VALID_SAMPLE_RATES = [8000, 16000, 22050, 24000, 32000, 44100, 48000]
VALID_FORMATS = ["mp3", "ogg_opus", "pcm"]


def synthesize(
    text: str,
    speaker: str,
    app_id: str,
    access_key: str,
    resource_id: str = "seed-icl-1.0",
    audio_format: str = "mp3",
    sample_rate: int = 24000,
    speech_rate: int = 0,
    loudness_rate: int = 0,
    pitch: int = 0,
    output_path: str = "output.mp3",
    model: str = "",
) -> str:
    """
    调用豆包语音合成 API 合成音频。

    Args:
        text: 待合成文本
        speaker: 音色 ID（如 S_9W2ToNVW1 或官方音色名）
        app_id: 火山引擎 APP ID
        access_key: 火山引擎 Access Token
        resource_id: 资源 ID（如 seed-icl-1.0）
        audio_format: 音频格式 mp3/ogg_opus/pcm
        sample_rate: 采样率
        speech_rate: 语速 [-50, 100]
        loudness_rate: 音量 [-50, 100]
        pitch: 音调 [-12, 12]
        output_path: 输出文件路径
        model: 模型版本（如 seed-tts-1.1）

    Returns:
        输出文件的路径
    """
    # 构建请求头
    request_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Id": app_id,
        "X-Api-Access-Key": access_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
    }

    # 构建请求体
    req_params = {
        "text": text,
        "speaker": speaker,
        "audio_params": {
            "format": audio_format,
            "sample_rate": sample_rate,
            "speech_rate": speech_rate,
            "loudness_rate": loudness_rate,
        },
    }

    # 可选: 模型版本
    if model:
        req_params["model"] = model

    # 可选: 音调调整
    if pitch != 0:
        req_params["additions"] = json.dumps({"post_process": {"pitch": pitch}})

    payload = {
        "user": {"uid": "skill_user"},
        "req_params": req_params,
    }

    print(f"[INFO] 开始合成语音...")
    print(f"[INFO] 音色: {speaker}")
    print(f"[INFO] 资源 ID: {resource_id}")
    print(f"[INFO] 格式: {audio_format}, 采样率: {sample_rate}")
    print(f"[INFO] 文本长度: {len(text)} 字符")
    print(f"[INFO] Request ID: {request_id}")

    # 使用 Session 实现连接复用（官方最佳实践）
    session = requests.Session()

    try:
        response = session.post(API_URL, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        sys.exit(1)

    # 解析流式响应，收集音频数据
    audio_chunks = []
    final_code = None
    final_message = None
    usage_info = None

    for line in response.iter_lines():
        if not line:
            continue

        try:
            data = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[WARN] 解析响应行失败: {e}")
            continue

        code = data.get("code", 0)
        message = data.get("message", "")

        # 合成结束标志
        if code == 20000000:
            final_code = code
            final_message = message
            usage_info = data.get("usage")
            print(f"[INFO] 合成完成: {message}")
            break

        # 错误处理
        if code != 0:
            print(f"[ERROR] 合成错误 code={code}: {message}")
            sys.exit(1)

        # 收集音频数据
        audio_data = data.get("data")
        if audio_data:
            try:
                chunk = base64.b64decode(audio_data)
                audio_chunks.append(chunk)
            except Exception as e:
                print(f"[WARN] 解码音频数据失败: {e}")

    if not audio_chunks:
        print("[ERROR] 未收到任何音频数据")
        sys.exit(1)

    # 拼接并保存音频
    audio_bytes = b"".join(audio_chunks)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    file_size_kb = len(audio_bytes) / 1024
    print(f"[INFO] 音频已保存: {output_path} ({file_size_kb:.1f} KB)")

    if usage_info:
        print(f"[INFO] 用量信息: {usage_info}")

    # 获取 logid 用于问题排查
    logid = response.headers.get("X-Tt-Logid", "N/A")
    print(f"[INFO] 服务端 LogID: {logid}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="豆包语音合成（火山引擎 Seed-TTS）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用声音复刻音色合成
  python3 tts_synthesize.py --text "你好，欢迎使用豆包语音合成" --speaker S_9W2ToNVW1

  # 使用官方预置音色
  python3 tts_synthesize.py --text "Hello world" --speaker zh_female_shuangkuaisisi_moon_bigtts --resource-id seed-tts-1.0

  # 调整语速和音量
  python3 tts_synthesize.py --text "这是一段测试" --speaker S_9W2ToNVW1 --speech-rate 20 --loudness-rate 10

  # 指定输出格式和路径
  python3 tts_synthesize.py --text "测试" --speaker S_9W2ToNVW1 --format ogg_opus --output my_audio.ogg
        """,
    )

    parser.add_argument("--text", required=True, help="待合成的文本内容")
    parser.add_argument("--speaker", default="S_9W2ToNVW1", help="音色 ID（默认: S_9W2ToNVW1）")
    parser.add_argument(
        "--resource-id",
        default="seed-icl-1.0",
        help="资源 ID（声音复刻用 seed-icl-1.0，官方1.0用 seed-tts-1.0，官方2.0用 seed-tts-2.0）",
    )
    parser.add_argument("--format", default="mp3", choices=VALID_FORMATS, help="音频格式（默认: mp3）")
    parser.add_argument(
        "--sample-rate", type=int, default=24000, choices=VALID_SAMPLE_RATES, help="采样率（默认: 24000）"
    )
    parser.add_argument("--speech-rate", type=int, default=0, help="语速 [-50, 100]（默认: 0）")
    parser.add_argument("--loudness-rate", type=int, default=0, help="音量 [-50, 100]（默认: 0）")
    parser.add_argument("--pitch", type=int, default=0, help="音调 [-12, 12]（默认: 0）")
    parser.add_argument("--output", default="output.mp3", help="输出文件路径（默认: output.mp3）")
    parser.add_argument("--model", default="", help="模型版本（如 seed-tts-1.1）")
    parser.add_argument("--app-id", default=None, help="APP ID（也可通过 DOUBAO_APP_ID 环境变量设置）")
    parser.add_argument("--access-key", default=None, help="Access Key（也可通过 DOUBAO_ACCESS_KEY 环境变量设置）")

    args = parser.parse_args()

    # 获取认证信息
    app_id = args.app_id or os.environ.get("DOUBAO_APP_ID")
    access_key = args.access_key or os.environ.get("DOUBAO_ACCESS_KEY")

    if not app_id:
        print("[ERROR] 未设置 APP ID。请通过 --app-id 参数或 DOUBAO_APP_ID 环境变量提供。")
        print("  获取方式: 登录火山引擎控制台 → 豆包语音 → 应用管理 → 获取 APP ID")
        sys.exit(1)

    if not access_key:
        print("[ERROR] 未设置 Access Key。请通过 --access-key 参数或 DOUBAO_ACCESS_KEY 环境变量提供。")
        print("  获取方式: 登录火山引擎控制台 → 豆包语音 → 应用管理 → 获取 Access Token")
        sys.exit(1)

    # 参数校验
    if not args.text.strip():
        print("[ERROR] 文本内容不能为空")
        sys.exit(1)

    if not -50 <= args.speech_rate <= 100:
        print("[ERROR] 语速范围为 [-50, 100]")
        sys.exit(1)

    if not -50 <= args.loudness_rate <= 100:
        print("[ERROR] 音量范围为 [-50, 100]")
        sys.exit(1)

    if not -12 <= args.pitch <= 12:
        print("[ERROR] 音调范围为 [-12, 12]")
        sys.exit(1)

    # 执行合成
    synthesize(
        text=args.text,
        speaker=args.speaker,
        app_id=app_id,
        access_key=access_key,
        resource_id=args.resource_id,
        audio_format=args.format,
        sample_rate=args.sample_rate,
        speech_rate=args.speech_rate,
        loudness_rate=args.loudness_rate,
        pitch=args.pitch,
        output_path=args.output,
        model=args.model,
    )


if __name__ == "__main__":
    main()
