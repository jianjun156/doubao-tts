---
name: doubao-tts
description: 使用豆包（火山引擎）语音合成大模型 API 将文本转换为语音音频文件。支持声音复刻音色（S_ 开头的音色ID）和官方预置音色。当用户要求"语音合成"、"文字转语音"、"TTS"、"朗读文本"、"生成语音"、"用我的声音读"、"豆包语音"、"声音复刻合成"等相关请求时，务必使用此 skill。即使用户只是说"帮我把这段话读出来"或"生成一段音频"，也应触发此 skill。
---

# 豆包语音合成 Skill（Doubao TTS）

本 skill 通过火山引擎豆包语音合成大模型的**单向流式 HTTP V3 接口**，将文本合成为语音音频文件。

## 前置要求

用户需要提供以下环境变量（通过 `export` 设置或在脚本参数中传入）：

- `DOUBAO_APP_ID`：火山引擎控制台获取的 APP ID
- `DOUBAO_ACCESS_KEY`：火山引擎控制台获取的 Access Token

如果用户没有设置这些环境变量，**先提醒用户设置**，并告知获取方式：登录火山引擎控制台 → 豆包语音 → 创建应用 → 获取 APP ID 和 Access Token。

## 使用流程

### 1. 确认参数

向用户确认以下信息（有合理默认值的可以跳过确认）：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 待合成文本 | 要转语音的文字内容 | （必填） |
| 音色 ID（speaker） | 音色标识符。声音复刻音色以 `S_` 开头 | `S_9W2ToNVW1` |
| 资源 ID（resource_id） | 声音复刻用 `seed-icl-1.0`；官方 1.0 音色用 `seed-tts-1.0`；官方 2.0 音色用 `seed-tts-2.0` | `seed-icl-1.0` |
| 音频格式（format） | `mp3` / `ogg_opus` / `pcm` | `mp3` |
| 采样率（sample_rate） | 可选 8000/16000/22050/24000/32000/44100/48000 | `24000` |
| 输出文件名 | 生成的音频文件名 | `output.mp3` |

### 2. 执行合成

运行脚本：

```bash
python3 /path/to/doubao-tts/scripts/tts_synthesize.py \
  --text "要合成的文本" \
  --speaker "S_9W2ToNVW1" \
  --resource-id "seed-icl-1.0" \
  --format mp3 \
  --sample-rate 24000 \
  --output /mnt/user-data/outputs/output.mp3
```

环境变量 `DOUBAO_APP_ID` 和 `DOUBAO_ACCESS_KEY` 必须已设置。也可以通过 `--app-id` 和 `--access-key` 参数直接传入。

### 3. 输出结果

脚本会将合成的音频保存到指定路径。合成完成后，使用 `present_files` 工具将文件呈现给用户。

## 重要注意事项

- **声音复刻音色**（S_ 开头）必须使用 `seed-icl-1.0` 作为 resource_id，不能用 `seed-tts-1.0`
- 如果用户提供的文本非常长（超过 5000 字），建议分段合成后拼接
- 脚本使用 `requests.Session` 实现连接复用，符合官方最佳实践
- 流式接口返回的音频数据是 base64 编码的，脚本会自动解码拼接
- 如果用户要求调整语速、音量、音调等，可传入对应参数

## 错误处理

- `40402003`：文本超长，需要分段
- `40000001`：参数错误，检查音色 ID 和 resource_id 是否匹配
- `40300001`：鉴权失败，检查 APP ID 和 Access Key
- 出现 quota 相关错误：试用版用量已用完，需开通正式版
