# -*- coding: utf-8 -*-
"""字幕对齐最终版：word_timestamps + 贪心匹配 + 段偏移 + 长句切分"""
from faster_whisper import WhisperModel
import json, re, shutil, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
model = WhisperModel("small", device="cpu", compute_type="int8")

TRAD_MAP = str.maketrans('說這個發學員話們後經驗觀點題問答錯講聽覺記錄義習類萬與為產應當處劃邊界費達構備質燒腦換擇種標許讓師條選礎爭執導術議價買實總結壞礙證據書輸於雙對開關機級樂雲錢銀鋼鐵門間閱飛雞專業藝醫廠廣庫強聲臉優傷動務勝區參壓測報場步歲節層注塑',
                         '说这个发学员话们后经验观点题问答错讲听觉记录义习类万与为产应当处划边界费达构备质烧脑换择种标许让师条选础争执导术议价买实总结坏碍证据书输于双对开关机级乐云钱银钢铁门间阅飞鸡专业艺医厂广库强声脸优伤动务胜区参压测报场步岁节层注速')

SCRIPTS = {
    "p1": "问AI学东西，越学越废？有个MIT研究生，48小时啃完一个陌生领域——我把他的方法直接做成了工具。",
    "p2": "先说清楚：这个方法不是我发明的。最早是一个MIT研究生在X上发的，讲他怎么用AI四十八小时速成一个全新领域；抖音的「学习有了方法」把它讲成了中文，我刷到之后越想越值，干脆把它写成了一套AI skill。今天拆给你。",
    "p3": "一句大白话：skill就是写给AI的操作手册。平时你问AI学东西，它默认当老师，讲课给你听——这正是学不会的原因，它把最烧脑的活儿替你干了。而这套手册下了死命令：你不许讲课，你只许出题、判卷、逼学员自己思考。装好之后你对AI说一句「帮我速成某某领域」，它就自动切换成魔鬼考官。",
    "p4": "考官上任第一件事：先别让我讲课，你先喂饭。找五到十五份这个领域的权威资料——经典教材、官方文档、重磅论文，一股脑丢给AI，跟它约法三章：所有回答只能基于这些材料，引到哪份文件哪一节，必须标出处；材料里没有的，就说没有，不许编。因为AI有个毛病：一本正经地胡说八道。你不给它圈定范围，它就替你发明专家共识。喂了原始教材，等于给它的回答铺了一层防幻觉地板。",
    "p5": "第二步，对着考官问两个问题。第一问：根据这些资料，这个领域所有专家都同意的五条核心思维模型是什么？这叫找共识——五条到手，这个领域的地基你就踩上了。第二问更狠：专家们在哪三件事上吵得不可开交？双方最强的论据分别是什么？这叫找争议。记住一句话：一个行业的门槛，不在共识里，在争议里。新手背结论，高手记分歧——你知道哪里在吵架，才知道这门学问的边界画在哪。",
    "p6": "第三步是整个方法的灵魂：拷问循环。考官基于刚才的内容出十道理解题——注意，是应用题，不是名词解释。你用自己的话答，它按评分标准判卷：答错了，它不报答案，只问你——你的答案错在哪，漏了哪几个要点？逼你自己回去翻资料，重新作答。全对一轮还不算完：把之前的错题混上两三道新题，再考一轮，防的就是你那个短期记忆。全流程走完，你手里还会多两样东西：一张自己的知识盲区清单，和一份可以直接拿去跟行业专家对话的问题列表。",
    "p7": "三个坑提前说：一，让AI替你答——整个方法当场作废，考官不能替考；二，偷看评分标准——你会不自觉照着要点背，判卷就失效了；三，不喂语料就开问——它开始瞎编，你学到的全是错的。这三个坑，skill里都写成了红线。",
    "p8": "总结：喂教材防它瞎编，三问挖出共识和争议，拷问循环把知识焊进脑子。一句话记住：知识不是听会的，是被考会的。这套skill我已经开源了，仓库地址在评论区，你拿去让AI照着执行就行。",
}
DURS = {"p1":10.416,"p2":19.32,"p3":27.0,"p4":32.688,"p5":34.272,"p6":37.848,"p7":20.136,"p8":18.192}
PUNCT = set('，。？！：；、「」——…·,')

# 场景偏移
offsets = {}
acc = 0.0
for k in SCRIPTS:
    offsets[k] = round(acc, 3)
    acc += DURS[k] + 0.6

def split_long(sent, st, en):
    """句长>8s 时按字符比例在逗号处切成 2-3 段"""
    dur = en - st
    if dur <= 8:
        return [(sent, st, en)]
    # 找逗号/顿号位置
    cuts = [m.start() for m in re.finditer(r'[，、]', sent)]
    if not cuts:
        return [(sent, st, en)]
    n_parts = 2 if dur <= 13 else 3
    target = dur / n_parts
    parts, last = [], 0
    prev_cut = -1
    for cp in cuts:
        if cp - last >= target * 0.6:
            parts.append(sent[last:cp + 1])
            last = cp + 1
            if len(parts) == n_parts - 1:
                break
    parts.append(sent[last:])
    if len(parts) < 2:
        return [(sent, st, en)]
    total_chars = sum(len(p) for p in parts)
    result = []
    t = st
    for p in parts:
        share = len(p) / total_chars
        d = dur * share
        result.append((p, t, t + d))
        t += d
    return result

out = []
for seg, ref in SCRIPTS.items():
    segments, info = model.transcribe(f"{seg}.mp3", language="zh", word_timestamps=True)
    wchars = []
    for sp in segments:
        for w in sp.words:
            for ch in w.word:
                if ch.strip():
                    wchars.append((w.start, w.end, ch.translate(TRAD_MAP)))
    sentences = []
    for s0 in re.split(r'(?<=[。？！])', ref):
        for s1 in re.split(r'(?<=[；])', s0):
            if s1.strip():
                sentences.append(s1.strip())
    wi = 0
    off = offsets[seg]
    for sent in sentences:
        ref_chars = [c.translate(TRAD_MAP) for c in sent if c.strip() and c not in PUNCT]
        first_st, last_en = None, None
        for rc in ref_chars:
            found = False
            for k in range(wi, min(wi + 12, len(wchars))):
                if wchars[k][2] == rc:
                    if first_st is None:
                        first_st = wchars[k][0]
                    last_en = wchars[k][1]
                    wi = k + 1
                    found = True
                    break
            if not found:
                if wi < len(wchars):
                    if first_st is None:
                        first_st = wchars[wi][0]
                    last_en = wchars[wi][1]
                    wi += 1
        if first_st is None:
            continue
        # 全局时间 + 长句切分
        for part, st, en in split_long(sent, first_st, last_en):
            out.append({"start": round(off + st, 2), "end": round(off + en, 2), "text": part.strip()})

out.sort(key=lambda x: x['start'])
json.dump(out, open('ramp-ep1/public/subtitles.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
shutil.copy('ramp-ep1/public/subtitles.json', 'ramp-ep1/src/subtitles.json')
print('总句数:', len(out))
bad = 0
prev_end = 0
for o in out:
    d = o['end'] - o['start']
    flag = ''
    if d > 8.5: flag += ' [过长]'
    if d < 0.4: flag += ' [过短]'
    if o['start'] < prev_end - 0.3: flag += ' [倒流]'
    prev_end = o['end']
    if flag:
        bad += 1
        print('异常:', f"{o['start']:.1f}-{o['end']:.1f}({d:.1f}s)", o['text'][:25], flag)
print('异常句数:', bad, '/', len(out))
print('前3句:', [(o['start'], o['text'][:15]) for o in out[:3]])
