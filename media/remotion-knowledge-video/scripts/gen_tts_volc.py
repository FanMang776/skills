# -*- coding: utf-8 -*-
"""火山引擎豆包语音合成 2.0 适配层（新版控制台 API Key 鉴权）

产出与 skill 管线兼容：
  pN.mp3          — 音频（与 gen_subs_edgetts.py rebuild 模式对接）
  words-pN.json   — 词级时间戳 [{t,d,w}...]（同 edge-tts WordBoundary 格式）

用法: VOLC_TTS_API_KEY=xxx python gen_tts_volc.py
音色: 刘飞 2.0 = zh_male_liufei_uranus_bigtts (resource_id: seed-tts-2.0)
"""
import asyncio, base64, json, os, sys, uuid

import aiohttp

API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
RESOURCE_ID = "seed-tts-2.0"
SPEAKER = "zh_male_liufei_uranus_bigtts"  # 刘飞 2.0
SEGMENTS = [
    ("p1", "每开一个新会话，AI就把你忘得干干净净。不是bug，是所有LLM的默认设计。"),
    ("p2", "Redis今年押向AI基础设施，三件套第二件就是冲这个来的：Agent Memory，托管式Agent记忆服务——会话历史、用户画像、任务状态，全管。"),
    ("p3", "先回答一个问题：记忆这种东西，凭什么Redis来做？两个理由。第一，Agent每轮对话都要读记忆，频率比查数据库高一个量级，延迟必须毫秒级——这是Redis的主场。第二，记忆检索本质是向量查询，和第一集语义缓存用的是同一套向量底座。所以三件套不是三个产品，是一套底座上的三种用法。"),
    ("p4", "它接的是什么活。模型天生无状态，每次请求记忆都要塞进prompt带过去；所以用户口径要重复教，偏好、历史决策、任务状态，全靠开发者自己存——存哪、怎么检索、何时过期，每个应用重造轮子。记忆本质是个工程公式：存储+检索+注入。"),
    ("p5", "Agent Memory把记忆拆三层，各有各的存法。会话内：当前对话消息历史，按序读写；跨会话：用户长期画像——用什么模型、报什么错、定过什么口径，记一次长期生效；工作记忆：Agent执行任务的中间状态，中断能续跑。三层的读写模式完全不同，这正是大多数自研记忆做烂的原因——一个JSON文件硬存所有东西。"),
    ("p6", "对回前面的两个理由：消息历史用List按序进出；画像用Hash随取随改；「哪条记忆和当前问题相关」靠向量相似度——每轮对话前查一次，最相关的几条自动拼进上下文。全部毫秒级，Agent的体感就是「它记得我」。"),
    ("p7", "记忆功能两条红线。合规：用户没让记的敏感信息别记，且必须有删除入口——「被遗忘权」在Agent记忆上是真实需求。第二，记忆污染：随口一句气话被存成永久偏好，比失忆更伤。解法是给记忆带TTL和置信度：可过期、可衰减、可覆盖。"),
    ("p8", "总结：模型无状态，记忆是工程问题；三层各管一段，Agent Memory托管成毫秒级服务，和语义缓存共用一套底座。下期收官：Vector Sets——别再给向量数据库单独交钱。"),
]


async def synth(session, api_key, seg_id, text, attempts=4):
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }
    payload = {
        "req_params": {
            "text": text,
            "speaker": SPEAKER,
            "audio_params": {"format": "mp3", "sample_rate": 24000, "enable_subtitle": True},
        }
    }
    for i in range(attempts):
        audio, words, end_ok = bytearray(), [], False
        try:
            async with session.post(API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {(await resp.text())[:200]}")
                async for raw in resp.content:
                    line = raw.strip()
                    if not line:
                        continue
                    obj = json.loads(line.decode("utf-8"))
                    code = obj.get("code")
                    if code == 20000000:
                        end_ok = True
                        break
                    if code == 0:
                        if obj.get("data"):
                            audio += base64.b64decode(obj["data"])
                        # 实测：HTTP 单向流式接口的字幕在 sentence 字段（文档写的 TTSSubtitle 事件是 WS 接口的）
                        sentence = obj.get("sentence") or {}
                        for w in sentence.get("words") or []:
                            if w.get("word"):
                                # 时间单位秒，相对整个 session
                                words.append({"t": float(w["startTime"]), "d": float(w["endTime"]) - float(w["startTime"]), "w": w["word"]})
                    else:
                        raise RuntimeError(f"业务错误 code={code}: {obj.get('message')}")
            if audio:
                open(f"{seg_id}.mp3", "wb").write(bytes(audio))
                json.dump(words, open(f"words-{seg_id}.json", "w", encoding="utf-8"), ensure_ascii=False)
                return len(words)
            raise RuntimeError("空音频")
        except Exception as e:
            print(f"  [{seg_id}] attempt {i+1} failed: {e}", flush=True)
            await asyncio.sleep(5 + i * 10)
    raise RuntimeError(f"{seg_id} failed after {attempts} attempts")


async def main():
    api_key = os.environ.get("VOLC_TTS_API_KEY")
    if not api_key:
        sys.exit("需要环境变量 VOLC_TTS_API_KEY")
    only = sys.argv[1:] or [s for s, _ in SEGMENTS]
    async with aiohttp.ClientSession() as session:
        for seg_id, text in SEGMENTS:
            if seg_id not in only:
                continue
            n = await synth(session, api_key, seg_id, text)
            print(f"[{seg_id}] ok, {n} word events, {os.path.getsize(f'{seg_id}.mp3')} bytes", flush=True)
            await asyncio.sleep(2)

asyncio.run(main())
