"""Build the checked-in curriculum. Language libraries are build-time only.

Usage: python tools/build_curriculum.py --sources ../research-data
Inputs and licenses are recorded in data/provenance.json. Never run at app startup.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from opencc import OpenCC
from pypinyin import Style, lazy_pinyin, pinyin
from pypinyin.contrib.tone_convert import to_normal, to_tone3

ROOT = Path(__file__).resolve().parents[1]
HK = OpenCC("s2hk")
SIMPLIFIED = OpenCC("t2s")
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]")
DICT_LINE = re.compile(r"^(\S+) (\S+) \[([^]]+)\] \{([^}]+)\}(?: /(.+)/)?")


def simplified(text: str) -> str:
    # OpenCC's rarely used extension-B simplification of 嗰 has no Cantonese
    # reading in Unihan. Retain the usual Cantonese glyph in simplified mode.
    return SIMPLIFIED.convert(text).replace("𠮶", "嗰")

# Explicit words take precedence over the English/POS fallback. Themes are
# learning aids, not official HSK subject divisions.
THEMES = {
    "Greetings & politeness": "你好 再见 谢谢 不客气 对不起 没关系 欢迎 客气 恭喜 祝贺 打招呼 抱歉 祝 顺便 请",
    "People & family": "我 你 您 他 她 它 我们 你们 他们 大家 谁 人 男人 女人 男 女 孩子 儿子 女儿 爸爸 妈妈 哥哥 姐姐 弟弟 妹妹 丈夫 妻子 爱人 爷爷 奶奶 孙子 叔叔 阿姨 先生 小姐 朋友 客人 邻居 亲戚 亲爱 年轻 年纪 家庭 结婚 离婚 出生 人口 互相 父亲 母亲 儿童 关系",
    "Food & drink": "吃 喝 菜 茶 水 饭 米饭 面条 面包 饺子 包子 苹果 香蕉 西瓜 葡萄 草莓 水果 蔬菜 鸡蛋 肉 羊肉 牛肉 鱼 鸡 猪 咖啡 牛奶 啤酒 红酒 饮料 果汁 糖 盐 油 厨房 厨师 餐厅 饭馆 饱 饿 甜 苦 酸 辣 味道 好吃 新鲜 营养 盘子 碗 筷子 勺子 杯子 瓶子 矿泉水 巧克力 饼干 香蕉 番茄 土豆 早饭 午饭 晚饭 汤 剩 烤 炸 尝",
    "Numbers & money": "零 一 二 三 四 五 六 七 八 九 十 百 千 万 两 第一 第二 半 双 一半 数字 数 数量 几 多少 钱 元 块 角 分 买 卖 贵 便宜 价格 打折 现金 信用卡 银行 支付 付款 收入 工资 经济 赚 花费 免费 购物 商店 超市 便宜 人民币 还 付 找钱 多少钱",
    "Time & routines": "现在 今天 明天 昨天 后天 前天 时候 时间 点 分钟 秒 小时 年 月 日 号 星期 周 周末 上午 中午 下午 晚上 早上 早晨 早 晚 刚才 刚刚 以后 以前 已经 正在 过去 将来 最近 最后 最初 经常 常常 总是 有时候 从来 平时 每 天 春节 节日 生日 假期 一会儿 后来 马上 突然 提前 按时 及时 永远 暂时 终于 立刻 期间 同时 时代 世纪 年代 目前 原来 先 后 越来越 结束 开始 睡觉 起床",
    "Travel & places": "北京 中国 香港 地方 哪儿 哪里 这里 那里 这儿 那儿 城市 国家 世界 国外 出国 机场 飞机 火车 公共汽车 出租车 地铁 车站 船 自行车 票 旅游 旅行 出发 到达 行李 护照 地图 方向 路 走 远 近 距离 交通 司机 开车 航班 高速公路 堵车 乘坐 公路 宾馆 酒店 参观 长城 门票 风景 导游 签证 旅馆 参观 回 来 去 进 出 到 离 地址 附近 停车 厕所 入口 出口 大使馆 首都 省 亚洲 欧洲",
    "Home & clothing": "家 房子 房间 门 窗户 桌子 椅子 床 沙发 灯 电视 冰箱 空调 洗衣机 电梯 阳台 客厅 卧室 住 搬 洗澡 洗 脏 干净 打扫 扫地 衣服 裤子 裙子 鞋 帽子 衬衫 外套 袜子 戴 穿 被子 毛巾 肥皂 镜子 包 钥匙 伞 家具 玩具 毛 皮 箱子 礼物 东西 物品 装 修理 收拾 整理 牙膏 租 号码",
    "School & work": "学 学习 学校 学生 老师 同学 书 读书 写 字 汉字 课 上课 下课 教室 教 学期 作业 考试 问题 回答 答案 题 分数 成绩 数学 历史 科学 知识 语言 词语 句子 拼音 汉语 中文 普通话 英语 大学 教授 校长 图书馆 本 笔 铅笔 纸 黑板 工作 公司 上班 下班 会议 办公室 同事 经理 职业 任务 职位 招聘 申请 面试 简历 专业 毕业 教育 法律 律师 工厂 生意 项目 计划 活动 复习 练习 测试 注意 经验 负责 完成 提高 认真 努力 秘书 规定 研究 讨论 讲座 总结 预习 技术 课程 报名 招聘",
    "Communication & ideas": "说 说话 话 告诉 听 问 回答 介绍 解释 表示 意思 意见 建议 看法 觉得 认为 知道 了解 明白 理解 记得 忘记 想 相信 希望 决定 同意 不同意 选择 比较 考虑 解决 发现 猜 证明 说明 认识 联系 打电话 电话 电子邮件 信息 消息 新闻 广告 报纸 杂志 网站 上网 语言 聊天 交流 词典 商量 声音 笑话 提醒 鼓励 批评 表扬 反对 支持 影响 印象 主意 理想 目的 原因 结果 方法 办法 机会 梦 想法 判断 重点 内容 复杂 标准 实际 例如 共同",
    "Health & feelings": "身体 头 头发 脸 眼睛 耳朵 鼻子 嘴 手 脚 腿 胳膊 心 牙 口 医院 医生 护士 病 生病 健康 药 发烧 感冒 疼 痛 牙疼 肚子 感觉 舒服 难受 累 渴 高兴 快乐 难过 伤心 生气 害怕 担心 紧张 放松 爱 喜欢 满意 幸福 感动 心情 激动 兴奋 孤单 后悔 失望 无聊 可惜 着急 耐心 信心 烦恼 压力 危险 安全 休息 照顾 保护 锻炼 运动 检查 受伤 轻松 成功 失败 停止 鼓掌 可怜 情况 困难",
    "Nature & animals": "天气 下雨 雨 雪 风 云 冷 热 晴 阴 太阳 月亮 星星 山 水河 河 海 树 花 草 叶子 森林 环境 空气 自然 季节 春 夏 秋 冬 地球 温度 气候 动物 猫 狗 鸟 熊猫 老虎 马 牛 羊 猪 龙 鱼 虫 蝴蝶 猴子 兔子 地 花园 公园 沙漠 湖 洋 阳光 植物 保护 浪费 节约 污染 地理 石头 农村 农民 水平 种 样子 湿润 干燥 零下 沙子",
    "Hobbies & entertainment": "看 电影 看电影 电视 看电视 唱歌 跳舞 音乐 歌 游戏 玩 玩儿 游泳 跑步 足球 篮球 踢足球 打篮球 乒乓球 网球 体育 比赛 运动会 音乐会 表演 演员 节目 观众 唱 弹钢琴 钢琴 照相 照片 爱好 兴趣 画 画画 故事 小说 书法 阅读 逛街 聚会 散步 爬山 骑 骑车 旅行 艺术 相声 排球 羽毛球 象棋 俱乐部 赢 输 聊天 举行 热闹 无聊",
    "Descriptions & colours": "大 小 多 少 长 短 高 矮 胖 瘦 快 慢 好 坏 新 旧 漂亮 美丽 丑 可爱 聪明 笨 重要 容易 难 简单 清楚 特别 非常 十分 真 最 更 太 很 比 一样 不同 颜色 红 黄 蓝 绿 黑 白 轻 重 便宜 贵 干净 脏 方便 合适 普通 一般 奇怪 一定 肯定 大概 可能 正确 错 错误 差 厚 薄 深 浅 宽 窄 丰富 完美 真实 严格 精彩 质量 顺利 优秀 假 严重 清晰 详细 正常 及时 充分 合理 礼貌 积极 消极 基本 主要 特殊 幽默 活泼 诚实 富 穷 空 满 整齐 整个",
    "Position & direction": "上 下 左 右 前 后 中 里面 外面 旁边 对面 中间 附近 东 南 西 北 东西 南北 位置 放 挂 站 坐 躺 排 排队 排列 顺序 超过 经过 通过 遍 周围 当地 到处 之内 以外 对于 关于",
    "Grammar & connectors": "的 了 吗 呢 吧 啊 着 过 得 地 和 跟 与 也 都 不 没 有 是 在 再 又 就 才 还 只 为了 因为 所以 但是 可是 虽然 如果 那么 还是 或者 而且 然后 除了 无论 不管 不仅 即使 只要 只有 是否 并且 尽管 然而 否则 于是 由于 因此 以 以及 把 被 让 对 给 从 向 往 比 按照 根据 作为 一边 一直 一起 一下 一些 其他 每 各 什么 怎么 为什么 怎么样 这样 那样 这种 那种 这 那 个 些 件 位 次 条 张 台 辆 把 座 层 趟 篇 所 份 段 门 只 支 片 颗 之一 而 不得不 来得及 来不及 往往 竟然 甚至 到底 仍然 并 任何 所有 全部 另 另外 足够 差不多 尤其 稍微 恐怕 好像 至少 一切 正好 总共 连 比如 左右 也许 必须 需要 应该 能 能够 可以 会 要 愿意 敢 值得 适合 允许 不要 别 尽量 实在 究竟 本来 往往 差点儿 几乎 究竟 非 不必 总 要是 随着 关于 关于 以上 以下 既然 既 不但 并 正 究竟 例如 光 光是 一般来说 不一定",
    "Actions & daily life": "做 打 开 关 帮助 用 等 等等 等待 拿 带 送 找 换 借 还 接 取 收 丢 放 弄 碰 见 面 抓 拉 推 交 选 检查 参加 加入 准备 打算 帮忙 离开 回来 回去 见面 起 起来 回答 练 试 试试 试验 重复 继续 保持 改变 增加 减少 进行 发展 出现 发生 产生 提供 拒绝 接受 坚持 扔 寄 破 使 死 活 打印 复印 下载 安排 管理 处理 解决 组织 分开 包括 解释 扩大 代替 记 记录 生长 留 留下 省 存 关心 逗 丢失 捡 占 负责 反映 完成 实现 克服 配合 合作 补充 购买 敲 擦 煮 摸",
}
KEYWORDS = {
    "Food & drink": ("food", "drink", "meal", "vegetable", "fruit", "rice", "restaurant", "kitchen", "bread", "wine", "meat", "soup"),
    "People & family": ("family", "relative", "person", "wife", "husband", "friend", "neighbor", "child", "parent"),
    "School & work": ("school", "student", "teacher", "work", "job", "company", "exam", "study", "education", "university", "business", "profession"),
    "Travel & places": ("travel", "transport", "country", "city", "train", "airport", "flight", "street", "hotel", "ticket", "vehicle"),
    "Time & routines": ("time", "morning", "evening", "month", "year", "holiday", "season", "week", "yesterday", "tomorrow"),
    "Home & clothing": ("house", "clothes", "clothing", "furniture", "room", "shirt", "trousers", "skirt"),
    "Health & feelings": ("health", "illness", "sick", "emotion", "happy", "sad", "worry", "fear", "body", "medical", "pain"),
    "Nature & animals": ("animal", "weather", "rain", "snow", "bird", "plant", "tree", "mountain", "environment", "river"),
    "Hobbies & entertainment": ("sport", "music", "movie", "film", "game", "dance", "entertain", "hobby", "novel"),
    "Communication & ideas": ("meaning", "explain", "discuss", "idea", "opinion", "language", "communicat", "news", "information"),
    "Numbers & money": ("money", "price", "cost", "bank", "number", "salary", "pay", "buy", "sell"),
}


def numbered(reading: str) -> str:
    return " ".join(to_tone3(x, neutral_tone_with_five=True).lower() for x in reading.split())


def clean_meaning(values: list[str]) -> str:
    values = [x.strip() for x in values if x and not re.search(r"CL:|\[[a-zāáǎàēéěèīíǐìōóǒòūúǔùü]+", x, re.I)]
    # HSK lists split some explanatory parentheses into separate items. Choose
    # a readable brief sense; keep the unabridged source senses in each entry.
    selected = []
    for x in values:
        if len(x) > 110 or x.count("(") != x.count(")") or x.startswith(("as opposed", "periodicals", "files etc")):
            continue
        selected.append(x)
        if len(selected) == 3:
            break
    return "; ".join(selected or values[:1])


def load_unihan(path: Path) -> dict:
    result = defaultdict(dict)
    for line in path.read_text().splitlines():
        if line.startswith("U+"):
            code, prop, value = line.split("\t", 2)
            result[chr(int(code[2:], 16))][prop] = value
    return result


def load_canto(paths: list[Path]) -> tuple[dict, dict]:
    words, singles = defaultdict(list), defaultdict(set)
    for path in paths:
        for line in path.read_text().splitlines():
            m = DICT_LINE.match(line)
            if not m:
                continue
            trad, simp, mandarin, canto, gloss = m.groups()
            record = {"jyutping": canto.lower(), "pinyin": mandarin.lower(), "gloss": gloss or ""}
            for key in dict.fromkeys([simp, trad, HK.convert(simp)]):
                words[key].append(record)
                if len(key) == 1 and re.fullmatch(r"[a-z]+[1-6]", canto.lower()):
                    singles[key].add(canto.lower())
    return words, singles


def sentence_index(path: Path, traditional: bool) -> dict:
    # Build an inverted index once, using native corpus rows and original
    # row-level attribution. A search hit is not a claim of syllabus coverage.
    by_glyph = defaultdict(list)
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        english, text, attribution = parts
        if not 3 <= len(text) <= 65 or len(english) > 180:
            continue
        converted = HK.convert(text) if traditional else simplified(text)
        record = {"simplified": simplified(text), "traditional": HK.convert(text), "english": english,
                  "attribution": attribution, "source": "Tatoeba", "license": "CC BY 2.0 FR"}
        for glyph in set(CJK.findall(converted)):
            by_glyph[glyph].append((converted, record))
    for rows in by_glyph.values():
        rows.sort(key=lambda row: (abs(len(row[0]) - 13), len(row[0]), row[0]))
    return by_glyph


def example(word: str, language: str, index: dict, authored: dict | None = None) -> dict:
    if authored:
        return {"simplified": simplified(authored["text"]), "traditional": HK.convert(authored["text"]),
                "english": authored["english"], "attribution": "First 1000 contributors — original example", "source": "Original", "license": "CC BY-SA 3.0"}
    search = simplified(word) if language == "mandarin" else HK.convert(word)
    candidates = index.get(search[0], [])
    for text, record in candidates:
        if search in text:
            return dict(record)
    # Honest reference example rather than an invented corpus translation.
    text = f'「{word}」是什么意思？' if language == "mandarin" else f'「{word}」即係咩意思？'
    return {"simplified": simplified(text), "traditional": HK.convert(text), "english": f'What does “{word}” mean?',
            "attribution": "First 1000 contributors — original reference sentence", "source": "Reference", "license": "CC BY-SA 3.0"}


def classify(word: str, meanings: str, pos: list, assignments: dict) -> str:
    if word in assignments:
        return assignments[word]
    english = meanings.lower()
    for theme, keywords in KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(k), english) for k in keywords):
            return theme
    if "a" in pos or "ad" in pos:
        return "Descriptions & colours"
    if "c" in pos or "p" in pos or "u" in pos or "q" in pos:
        return "Grammar & connectors"
    if "v" in pos:
        return "Actions & daily life"
    return "Communication & ideas"


def build(sources: Path) -> dict:
    unihan = load_unihan(sources / "Unihan_Readings.txt")
    canto_words, canto_singles = load_canto([sources / "cccedict-canto-readings-150923.txt", sources / "cccanto-webdist.txt"])
    cmn = sentence_index(sources / "cmn.txt", False)
    yue = sentence_index(sources / "yue.txt", True)
    hk_words = json.loads((sources / "hk-curated.json").read_text())
    overrides = json.loads((sources / "cantonese-overrides.json").read_text())
    if isinstance(overrides, list):
        overrides = {x["mandarin_simplified"]: x for x in overrides}
    assignments = {word: theme for theme, words in THEMES.items() for word in words.split()}
    rich = {x["simplified"]: x for level in range(1, 5) for x in json.loads((sources / f"hsk-old-{level}.json").read_text())}
    entries, groups = {}, defaultdict(list)
    hanzi = list(csv.DictReader((sources / "hanzi_db.csv").open()))
    top = hanzi[:1000]
    ranks = {x["character"]: int(x["frequency_rank"]) for x in hanzi}

    def jyutping(word: str, pinyin_numbers: str | None = None) -> str:
        records = canto_words.get(word) or canto_words.get(simplified(word)) or []
        if pinyin_numbers:
            comparable = pinyin_numbers.replace("5", "").replace(" ", "")
            matched = [r for r in records if r["pinyin"].replace("5", "").replace(" ", "") == comparable]
            if matched:
                records = matched
        if records:
            return records[0]["jyutping"]
        readings = []
        for ch in word:
            if not CJK.fullmatch(ch):
                continue
            reading = unihan.get(ch, {}).get("kCantonese")
            if not reading:
                reading = unihan.get(simplified(ch), {}).get("kCantonese")
            if not reading:
                raise ValueError(f"Missing Cantonese reading: {word} / {ch}")
            readings.append(reading.split()[0])
        return " ".join(readings)

    for level in range(1, 5):
        for original in json.loads((sources / f"hsk-original-{level}.json").read_text()):
            word = original["hanzi"]
            entry_id = f"w:{word}"
            if entry_id in entries:
                entries[entry_id]["source_senses"].extend(original["translations"])
                continue
            data = rich.get(word, {})
            trad = HK.convert(word)
            pn = numbered(original["pinyin"])
            override = overrides.get(word, {})
            if override.get("mandarin_numeric_restriction") and override["mandarin_numeric_restriction"].replace(" ", "") != pn.replace(" ", ""):
                override = {}
            canto = override.get("cantonese_traditional", trad)
            meaning = override.get("english", clean_meaning(original["translations"]))
            if not meaning:
                meaning = {"个": "general measure word; individual", "关系": "relationship; connection"}.get(word, "")
            if not meaning:
                raise ValueError(f"No usable English sense for {word}")
            entry = {"id": entry_id, "kind": "vocabulary", "hsk": level, "frequency": data.get("frequency", 999999),
                     "english": meaning, "source_senses": original["translations"], "mandarin_simplified": word,
                     "mandarin_traditional": trad, "cantonese_simplified": simplified(canto), "cantonese_traditional": canto,
                     "pinyin": original["pinyin"], "pinyin_numbers": pn, "jyutping": override.get("jyutping") or jyutping(canto, pn),
                     "cantonese_register": "spoken Hong Kong" if override else "shared written vocabulary",
                     "usage_note": override.get("note", ""),
                     "examples": {"mandarin": example(word, "mandarin", cmn), "cantonese": example(canto, "cantonese", yue, override.get("example"))}}
            entries[entry_id] = entry
            theme = classify(word, meaning, data.get("pos", []), assignments)
            groups[("hsk", level, theme)].append(entry_id)
    vocabulary_ids = list(entries)
    for item in hk_words:
        word = item["cantonese_traditional"]
        entry_id = f"hk:{word}"
        mandarin = item["mandarin_simplified"]
        reading = item.get("pinyin") or " ".join(lazy_pinyin(mandarin, style=Style.TONE))
        entries[entry_id] = {"id": entry_id, "kind": "hong_kong", "hsk": None,
            "frequency": rich.get(mandarin, {}).get("frequency", 999999), "english": item["english"],
            "mandarin_simplified": mandarin, "mandarin_traditional": HK.convert(mandarin),
            "cantonese_simplified": simplified(word), "cantonese_traditional": word,
            "pinyin": reading, "pinyin_numbers": numbered(reading), "jyutping": item["jyutping"], "cantonese_register": "spoken Hong Kong",
            "examples": {"mandarin": example(mandarin, "mandarin", cmn, item["examples"]["mandarin"]),
                         "cantonese": example(word, "cantonese", yue, item["examples"]["cantonese"])}}
        vocabulary_ids.append(entry_id)
        groups[("hk", 0, item["theme"])].append(entry_id)

    categories = []
    group_chunks = {key: [ids] for key, ids in sorted(groups.items())}
    # Preserve the recovered 93 small themed sets while keeping all questions
    # fixed after this build. Split largest sets first; never randomize membership.
    if len(group_chunks) > 93:
        raise ValueError(f"Too many theme groups: {len(group_chunks)}")
    while sum(map(len, group_chunks.values())) < 93:
        key, index = max(((key, i) for key, chunks in group_chunks.items() for i in range(len(chunks))), key=lambda pair: len(group_chunks[pair[0]][pair[1]]))
        chunk = group_chunks[key][index]
        midpoint = (len(chunk) + 1) // 2
        group_chunks[key][index:index+1] = [chunk[:midpoint], chunk[midpoint:]]
    for (kind, level, theme), chunks in group_chunks.items():
        slug = re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")
        for i, ids in enumerate(chunks):
            suffix = f" · Part {i+1}" if len(chunks) > 1 else ""
            categories.append({"id": f"{kind}-{level}-{slug}-{i+1}", "title": f"{theme} {level}{suffix}" if kind == "hsk" else f"Hong Kong · {theme}{suffix}",
                "theme": theme, "kind": "hong_kong" if kind == "hk" else "vocabulary", "hsk": level or None, "entry_ids": ids,
                "description": f"HSK (2012) level {level} · fixed vocabulary set" if level else "Everyday spoken Hong Kong Cantonese, with Mandarin equivalents"})

    for row in top:
        word = row["character"]
        entry_id = f"c:{word}"
        definition = row["definition"] or unihan[word].get("kDefinition", "")
        reading = row["pinyin"]
        trad = HK.convert(word)
        entries[entry_id] = {"id": entry_id, "kind": "character", "hsk": int(row["hsk_level"]) if row["hsk_level"].isdigit() else None,
            "frequency": int(row["frequency_rank"]), "english": definition, "mandarin_simplified": word, "mandarin_traditional": trad,
            "cantonese_simplified": word, "cantonese_traditional": trad, "pinyin": reading, "pinyin_numbers": numbered(reading), "jyutping": jyutping(trad),
            "cantonese_register": "character reading", "examples": {"mandarin": example(word, "mandarin", cmn), "cantonese": example(trad, "cantonese", yue)}}
    for i in range(40):
        categories.append({"id": f"core-{i+1:02}", "title": f"First 1000 · Set {i+1:02}", "theme": "First 1000", "kind": "characters", "hsk": None,
            "entry_ids": [f'c:{x["character"]}' for x in top[i*25:(i+1)*25]], "description": f"Frequency ranks {i*25+1}–{(i+1)*25} · 25 character cards"})

    target_ids = defaultdict(set)
    for row in top:
        for glyph in (row["character"], HK.convert(row["character"])):
            target_ids[glyph].add(row["character"])
    all_glyphs = {ch for e in entries.values() for key in ("mandarin_simplified", "mandarin_traditional", "cantonese_simplified", "cantonese_traditional") for ch in e[key] if CJK.fullmatch(ch)}
    characters = {}
    for glyph in sorted(all_glyphs):
        record = unihan.get(glyph, {})
        ps = pinyin(glyph, style=Style.TONE3, heteronym=True, neutral_tone_with_five=True, errors=lambda x: [x])[0]
        ps = [x.lower().replace("ü", "v") for x in ps if re.fullmatch(r"[a-zü]+[1-5]", x.lower())]
        if not ps and record.get("kMandarin"):
            ps = [numbered(record["kMandarin"].split()[0])]
        js = set(canto_singles.get(glyph, set()))
        js.update(record.get("kCantonese", "").split())
        js = sorted(x for x in js if re.fullmatch(r"[a-z]+[1-6]", x))
        if not ps or not js:
            raise ValueError(f"Missing drill reading for {glyph}: {ps} / {js}")
        characters[glyph] = {"pinyin": list(dict.fromkeys(ps)), "jyutping": js, "meaning": record.get("kDefinition", ""),
            "rank": ranks.get(glyph) or ranks.get(simplified(glyph)), "target_ids": sorted(target_ids[glyph])}
    coverage = {lang: dict(Counter(e["examples"][lang]["source"] for e in entries.values())) for lang in ("mandarin", "cantonese")}
    return {"schema": 1, "meta": {"title": "First 1000", "rebuilt_from_recovered_spec": True, "hsk_syllabus": "HSK 2012 (six-level syllabus), levels 1–4",
        "vocabulary_count": len(vocabulary_ids), "character_count": 1000, "category_count": len(categories), "example_coverage": coverage,
        "frequency_note": "Character ranks: HanziDB / Jun Da. Word ranks: source dictionary; Hong Kong-only phrases may be unranked.",
        "cantonese_note": "Spoken Hong Kong equivalents for curated everyday words; other HSK words are shared written vocabulary. Bare-character drills accept dictionary alternative readings."},
        "entries": list(entries.values()), "vocabulary_entry_ids": vocabulary_ids, "categories": categories,
        "target_characters": [x["character"] for x in top], "characters": characters}


def fonts(sources: Path, payload: dict):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    assets = ROOT / "src/assets/fonts"
    assets.mkdir(parents=True, exist_ok=True)
    texts = json.dumps(payload, ensure_ascii=False) + "千學学一千字你好歡迎学习粵語汉字漢字"
    font = TTFont(sources / "fonts/NotoSansCJKhk-Regular.otf")
    covered = set(font.getBestCmap())
    missing = {ord(x) for x in texts if CJK.fullmatch(x)} - covered
    if missing:
        raise ValueError(f"Font missing {len(missing)} glyphs")
    options = subset.Options()
    options.name_IDs = [0,1,2,3,4,5,6]
    sub = subset.Subsetter(options=options)
    sub.populate(text=texts)
    sub.subset(font)
    for record in font["name"].names:
        if record.nameID in (1, 3, 4, 6):
            value = "First1000Hanzi" if record.nameID == 6 else "First 1000 Hanzi"
            record.string = value.encode(record.getEncoding())
    font.save(assets / "First1000Hanzi.otf")
    shutil.copyfile(sources / "fonts/Inter-variable.ttf", assets / "Inter.ttf")
    for source, dest in [("NotoSansCJK-OFL.txt", "First1000Hanzi-OFL.txt"), ("Inter-OFL.txt", "Inter-OFL.txt")]:
        shutil.copyfile(sources / "fonts" / source, assets / dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.sources)
    out = ROOT / "src/first1000/data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "curriculum.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    manifest = json.loads((args.sources / "manifest.json").read_text())
    manifest["build_inputs"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.sources.glob("*-curated.json")}
    manifest["build_inputs"]["cantonese-overrides.json"] = hashlib.sha256((args.sources / "cantonese-overrides.json").read_bytes()).hexdigest()
    (out / "provenance.json").write_text(json.dumps(manifest, indent=2))
    curated = ROOT / "tools/curated"
    curated.mkdir(parents=True, exist_ok=True)
    for name in ("hk-curated.json", "cantonese-overrides.json"):
        shutil.copyfile(args.sources / name, curated / name)
    licenses = ROOT / "LICENSES"
    licenses.mkdir(exist_ok=True)
    for name in ("hanzi_db.LICENSE", "hsk.LICENSE", "hsk-original.LICENSE", "unicode.LICENSE"):
        shutil.copyfile(args.sources / name, licenses / name)
    fonts(args.sources, payload)
    print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))
