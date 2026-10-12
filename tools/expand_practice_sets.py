import json
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parents[1]/'src/first1000/data'
base=json.loads((root/'curriculum.json').read_text());extra=json.loads((root/'everyday.json').read_text())
entries={e['id']:e for e in base['entries']+extra['entries']};categories=base['categories']+extra['categories']
plans={
'paying-the-bill':('钱 信用卡 银行 服务员 菜单 元 块 买 卖 贵 便宜', ['Numbers & money','Food & drink']),
'ordering-food':('菜单 服务员 米饭 面条 鸡蛋 菜 肉 吃 喝 水 茶 饭馆', ['Food & drink']),
'cafe':('咖啡 茶 糖 杯子 牛奶 喝 热 冷 水 点 服务员', ['Food & drink']),
'shopping':('买 卖 钱 贵 便宜 商店 衣服 颜色 大 小 信用卡 需要', ['Numbers & money','Home & clothing']),
'directions':('左边 右边 前面 后面 近 远 路 走 找 火车站 地方 旁边', ['Position & direction','Travel & places']),
'transport':('票 地铁 火车 飞机 公共汽车 出租车 自行车 机场 出发 小时 分钟', ['Travel & places']),
'hotel':('宾馆 房间 护照 行李箱 住 热 水 早餐 服务员 床 洗澡', ['Travel & places','Home & clothing']),
'appointments':('明天 时间 小时 分钟 迟到 下午 见面 约会 医生 医院 等', ['Time & routines','Health & feelings']),
'meeting-people':('认识 名字 朋友 人 住 家 中国 国家 高兴 请问 介绍', ['People & family','Greetings & politeness']),
'making-plans':('明天 今天 一起 朋友 时间 周末 星期 电影 见面 吃饭 约会', ['Time & routines','Hobbies & entertainment']),
'asking-for-help':('帮忙 慢 明白 说话 听懂 谢谢 不好意思 知道 问题 回答 说', ['Greetings & politeness','Communication & ideas']),
'feeling-unwell':('医生 医院 药 病 身体 舒服 休息 睡觉 累 发烧 头疼', ['Health & feelings'])}
theme_alias={'Greetings & politeness':['Greetings & politeness','Communication & ideas'],'greetings':['Greetings & politeness','Communication & ideas'],'daily life':['Actions & daily life'],'food':['Food & drink'],'greetings':['Greetings & politeness','Communication & ideas'],'people':['People & family'],'politeness':['Greetings & politeness','Communication & ideas'],'questions':['Communication & ideas'],'time':['Time & routines'],'transport':['Travel & places']}
by_theme=defaultdict(list)
for cat in base['categories']:
    for eid in cat['entry_ids']:
        if entries[eid]['kind']!='character':by_theme[cat['theme']].append(eid)
sets={}
for cat in categories:
    ids=list(cat['entry_ids'])
    if len(ids)<15 and cat['kind'] not in ('characters','cantonese_characters'):
        explicit=[];themes=theme_alias.get(cat['theme'],[cat['theme']])
        if cat['kind']=='situations':
            terms,themes=plans[cat['id'].removeprefix('situation-')]
            explicit=['w:'+term for term in terms.split() if 'w:'+term in entries]
        pool=explicit+sorted(set(eid for theme in themes for eid in by_theme[theme]),key=lambda eid:(entries[eid].get('frequency') or 999999,eid))
        for eid in pool:
            if eid not in ids:ids.append(eid)
            if len(ids)>=15:break
        assert len(ids)>=15,cat['id']
    sets[cat['id']]=ids
(root/'practice_sets.json').write_text(json.dumps({'note':'Related vocabulary supplements small practice sets; original category memberships and trophy fingerprints are unchanged.','sets':sets},ensure_ascii=False,indent=2))
print('All',len(sets),'practice sets have at least 15 cards; all situation sets have',set(len(sets[c['id']]) for c in categories if c['kind']=='situations'))
