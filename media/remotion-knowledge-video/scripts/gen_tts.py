# -*- coding: utf-8 -*-
"""EP1 v2 TTS 分段生成：P1-P8 段独立 mp3，zh-CN-YunxiNeural +8%，输出时长表"""
import asyncio, json, subprocess, os

BASE = os.path.dirname(os.path.abspath(__file__))

SEGMENTS = {
    "p1": "问AI学东西，越学越废？有个MIT研究生，48小时啃完一个陌生领域——我把他的方法直接做成了工具。",
    "p2": "先说清楚：这个方法不是我发明的。最早是一个MIT研究生在X上发的，讲他怎么用AI四十八小时速成一个全新领域；抖音的「学习有了方法」把它讲成了中文，我刷到之后越想越值，干脆把它写成了一套AI skill。今天拆给你。",
    "p3": "一句大白话：skill就是写给AI的操作手册。平时你问AI学东西，它默认当老师，讲课给你听——这正是学不会的原因，它把最烧脑的活儿替你干了。而这套手册下了死命令：你不许讲课，你只许出题、判卷、逼学员自己思考。装好之后你对AI说一句「帮我速成某某领域」，它就自动切换成魔鬼考官。",
    "p4": "考官上任第一件事：先别让我讲课，你先喂饭。找五到十五份这个领域的权威资料——经典教材、官方文档、重磅论文，一股脑丢给AI，跟它约法三章：所有回答只能基于这些材料，引到哪份文件哪一节，必须标出处；材料里没有的，就说没有，不许编。因为AI有个毛病：一本正经地胡说八道。你不给它圈定范围，它就替你发明专家共识。喂了原始教材，等于给它的回答铺了一层防幻觉地板。",
    "p5": "第二步，对着考官问两个问题。第一问：根据这些资料，这个领域所有专家都同意的五条核心思维模型是什么？这叫找共识——五条到手，这个领域的地基你就踩上了。第二问更狠：专家们在哪三件事上吵得不可开交？双方最强的论据分别是什么？这叫找争议。记住一句话：一个行业的门槛，不在共识里，在争议里。新手背结论，高手记分歧——你知道哪里在吵架，才知道这门学问的边界画在哪。",
    "p6": "第三步是整个方法的灵魂：拷问循环。考官基于刚才的内容出十道理解题——注意，是应用题，不是名词解释。你用自己的话答，它按评分标准判卷：答错了，它不报答案，只问你——你的答案错在哪，漏了哪几个要点？逼你自己回去翻资料，重新作答。全对一轮还不算完：把之前的错题混上两三道新题，再考一轮，防的就是你那个短期记忆。全流程走完，你手里还会多两样东西：一张自己的知识盲区清单，和一份可以直接拿去跟行业专家对话的问题列表。",
    "p7": "三个坑提前说：一，让AI替你答——整个方法当场作废，考官不能替考；二，偷看评分标准——你会不自觉照着要点背，判卷就失效了；三，不喂语料就开问——它开始瞎编，你学到的全是错的。这三个坑，skill里都写成了红线。",
    "p8": "总结：喂教材防它瞎编，三问挖出共识和争议，拷问循环把知识焊进脑子。一句话记住：知识不是听会的，是被考会的。这套skill我已经开源了，仓库地址在评论区，你拿去让AI照着执行就行。关注我，下期拆：怎么把这个skill改成你的私人出题机器人。你上次用AI学东西，是让它讲，还是让它考？评论区聊聊。",
}

import edge_tts

async def gen(seg_id, text):
    out = os.path.join(BASE, f"{seg_id}.mp3")
    cm = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+8%")
    await cm.save(out)
    return out

async def main():
    durations = {}
    for seg_id, text in SEGMENTS.items():
        await gen(seg_id, text)
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", os.path.join(BASE, f"{seg_id}.mp3")],
            capture_output=True, text=True)
        durations[seg_id] = float(r.stdout.strip())
    with open(os.path.join(BASE, "tts-durations.json"), "w", encoding="utf-8") as f:
        json.dump(durations, f, indent=2)
    total = sum(durations.values())
    for k, v in durations.items():
        print(f"{k}: {v:.2f}s")
    print(f"TOTAL: {total:.2f}s ({total/60:.1f} min)")

asyncio.run(main())
