#!/usr/bin/env python3
"""
趣游卡机票扫描 - 精简版
扫描未来90天所有周末，输出到 stdout
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict

API_URL = "https://ecskgateway.ceair.com/openApi/redeemable/queryRedeemableDetailNew"
PARAMS = {
    "channelCode": "Nzg2MA==", "salesChannel": "Nzg2MA==",
    "productCode": "YRDCCN1025", "routeType": "OW", "indexNo": "1",
}
HEADERS = {
    "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache", "Content-Type": "application/json",
    "Origin": "https://ecactivity.ceair.com", "Pragma": "no-cache",
    "Referer": "https://ecactivity.ceair.com/",
    "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
}

CITY_CODE_MAP = [
    ("北京","BJS"),("上海","SHA"),("天津","TSN"),("重庆","CKG"),
    ("石家庄","SJW"),("太原","TYN"),("呼和浩特","HET"),("沈阳","SHE"),
    ("大连","DLC"),("长春","CGQ"),("哈尔滨","HRB"),
    ("南京","NKG"),("无锡","WUX"),("常州","CZX"),("南通","NTG"),
    ("徐州","XUZ"),("连云港","LYG"),("扬州","YTY"),("苏州","SZV"),
    ("杭州","HGH"),("宁波","NGB"),("温州","WNZ"),("舟山","HSN"),
    ("台州","HYN"),("金华","YIW"),("嘉兴","JXS"),("合肥","HFE"),
    ("黄山","TXN"),("福州","FOC"),("厦门","XMN"),("泉州","JJN"),
    ("南昌","KHN"),("赣州","KOW"),("九江","JIU"),
    ("济南","TNA"),("青岛","TAO"),("烟台","YNT"),("威海","WEH"),
    ("郑州","CGO"),("洛阳","LYA"),("武汉","WUH"),
    ("长沙","CSX"),("张家界","DYG"),
    ("广州","CAN"),("深圳","SZX"),("珠海","ZUH"),
    ("南宁","NNG"),("桂林","KWL"),("海口","HAK"),("三亚","SYX"),
    ("成都","CTU"),("绵阳","MIG"),
    ("贵阳","KWE"),
    ("昆明","KMG"),("丽江","LJG"),
    ("西安","SIA"),("兰州","LHW"),
    ("西宁","XNN"),
]

NAME_TO_CODE = {name: code for name, code in CITY_CODE_MAP}

def get_weekend_dates(days=90):
    """获取未来N天内的所有周末（周六+周日成对）"""
    weekends = []
    current = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = current + timedelta(days=days)
    while current <= end:
        if current.weekday() in (5, 6):
            weekends.append(current)
        current += timedelta(days=1)
    return weekends

def format_date(d):
    return d.strftime("%Y-%m-%d")

async def query(session, ori_code, des_code, dep_date):
    body = {"oriCityCode": ori_code, "desCityCode": des_code, "depDate": dep_date, **PARAMS}
    try:
        async with session.post(API_URL, json=body, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status != 200:
                return {}
            data = await resp.json()
            return data.get("data", {}).get("redeemableDetailMap", {})
    except:
        return {}

async def scan_route(session, ori_name, des_name, dates):
    ori_code = NAME_TO_CODE.get(ori_name)
    des_code = NAME_TO_CODE.get(des_name)
    if not ori_code or not des_code:
        return {}
    tasks = [query(session, ori_code, des_code, format_date(d)) for d in dates]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    route_results = {}
    for d, r in zip(dates, results):
        route_results[format_date(d)] = r.get(format_date(d)) if isinstance(r, dict) else None
    return route_results

def get_weekend_pairs(weekends):
    """把连续的周末日期合并成 {weekend_label: [sat_date, sun_date]}"""
    pairs = {}
    i = 0
    while i < len(weekends):
        d = weekends[i]
        if d.weekday() == 5:  # 周六
            sat_d = d
            sun_d = d + timedelta(days=1)
            # 检查周日是否存在且连续
            if i + 1 < len(weekends) and weekends[i+1] == sun_d:
                label = f"{sat_d.strftime('%m/%d')}-{sun_d.strftime('%m/%d')}"
                pairs[label] = [sat_d, sun_d]
                i += 2
                continue
            else:
                label = f"{sat_d.strftime('%m/%d')}(六)"
                pairs[label] = [sat_d]
                i += 1
                continue
        else:  # 周日
            label = f"{d.strftime('%m/%d')}(日)"
            pairs[label] = [d]
            i += 1
    return pairs

async def main():
    BASE = "上海"
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    weekends = get_weekend_dates(90)
    weekend_strs = [format_date(d) for d in weekends]
    date_labels = {format_date(d): ("六" if d.weekday() == 5 else "日") for d in weekends}

    cities = [name for name, _ in CITY_CODE_MAP if name != BASE]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始扫描 | 城市:{len(cities)} 日期:{len(weekend_strs)}个周末", flush=True)

    all_results = {}  # {(ori, des, date_str): status}

    async with aiohttp.ClientSession() as session:
        # 情景一：上海→北京
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 情景一：上海→北京", flush=True)
        r1 = await scan_route(session, BASE, "北京", weekends)
        for d, s in r1.items():
            all_results[(BASE, "北京", d)] = s

        # 情景一返程：北京→上海
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 情景一返程：北京→上海", flush=True)
        r2 = await scan_route(session, "北京", BASE, weekends)
        for d, s in r2.items():
            all_results[("北京", BASE, d)] = s

        # 情景二：上海→全量城市
        for i, city in enumerate(cities):
            if i % 20 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 情景二进度:{i+1}/{len(cities)}", flush=True)
            r = await scan_route(session, BASE, city, weekends)
            for d, s in r.items():
                all_results[(BASE, city, d)] = s

    # ── 按周末分组，生成老格式报告 ─────────────────────────
    weekend_pairs = get_weekend_pairs(weekends)
    SEP = ""

    lines = []
    lines.append(f"✈️ 趣游卡日报")
    lines.append(f"未来90天 · {len(weekend_pairs)}个周末 · {datetime.now().strftime('%m/%d %H:%M')}")
    lines.append("")
    lines.append(SEP)

    for label, dates in sorted(weekend_pairs.items()):
        lines.append(f"📅 {label}")

        # ── 上海↔北京 去程返程状态 ──
        # 只看周六去程（上海→北京）和周日返程（北京→上海）
        sat_d = dates[0]  # 周六
        sun_d = dates[1] if len(dates) > 1 else None  # 周日

        go_sat = all_results.get((BASE, "北京", format_date(sat_d))) == "2"
        back_sun = all_results.get(("北京", BASE, format_date(sun_d))) == "2" if sun_d else False

        status_parts = [f"去程{'✅' if go_sat else '❌'}"]
        if sun_d:
            status_parts.append(f"返程{'✅' if back_sun else '❌'}")
        status_line = "  ".join(status_parts)
        if go_sat and back_sun:
            status_line += "  🌟完整往返"

        lines.append(f"{BASE} ↔ 北京")
        lines.append(f"  {status_line}")

        # ── 按城市分类 ──
        round_cities = []    # 往返完整：周六有票+周日有票
        go_only = []         # 仅去程：只有周六有票
        back_only = []       # 仅返程：只有周日有票

        for city, _ in CITY_CODE_MAP:
            if city == BASE:
                continue
            sat_avail = False
            sun_avail = False
            for d in dates:
                if all_results.get((BASE, city, format_date(d))) == "2":
                    if d.weekday() == 5:
                        sat_avail = True
                    else:
                        sun_avail = True

            if sat_avail and sun_avail:
                round_cities.append(city)
            elif sat_avail:
                go_only.append(city)
            elif sun_avail:
                back_only.append(city)

        def fmt_cities(city_list):
            """把城市列表格式化成两行，每行末尾不断行"""
            if not city_list:
                return []
            # 每行最多5个城市，用 / 分隔
            result = []
            for i in range(0, len(city_list), 5):
                chunk = city_list[i:i+5]
                result.append("  " + " / ".join(chunk))
            return result

        if round_cities:
            lines.append("往返完整")
            lines.extend(fmt_cities(round_cities))
        if go_only:
            lines.append("仅去程")
            lines.extend(fmt_cities(go_only))
        if back_only:
            lines.append("仅返程")
            lines.extend(fmt_cities(back_only))

        lines.append("")
        lines.append(SEP)

    msg = "\n".join(lines)
    print(msg)
    return msg

if __name__ == "__main__":
    asyncio.run(main())
