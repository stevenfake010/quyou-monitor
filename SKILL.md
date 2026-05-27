---
name: quyou-monitor
description: 东航趣游卡机票监控 | Monitor China Eastern Airlines Miles redemption (趣游卡) availability for all domestic routes. Scans Shanghai as origin to 80+ cities for the next 90 days of weekends, detects ticket availability (status="2"), and delivers a formatted daily report via WeChat. Use when user asks about flight tickets, weekend getaways, 趣游卡, or 东航机票. Trigger phrases: 机票/趣游卡/东航/周末去哪/有票吗/航班
metadata:
  openclaw:
    requires:
      bins: [python3, aiohttp]
    homepage: https://github.com/stevenfake010/quyou-monitor
    emoji: ✈️
---

# 趣游卡机票监控 Skill

扫描东航趣游卡（积分兑换）未来90天内所有周末航线，检测上海出发至全国各城市的有票情况，生成格式化报告并推送微信。

**当前状态**：全量城市扫描已上线，上海↔北京往返优先显示，6月6日（含）起出行模式确认中断。

---

## 核心数据

| 项目 | 值 |
|---|---|
| API 地址 | `https://ecskgateway.ceair.com/openApi/redeable/queryRedeemableDetailNew` |
| 产品代码 | `YRDCCN1025` |
| 出发地 | 上海（SHA） |
| 扫描城市 | ~80个国内城市 |
| 扫描周期 | 未来90天所有周末（周六+周日） |
| 有票标识 | `status == "2"` |
| 推送渠道 | 微信（openclaw-weixin） |
| 推送账号 | `42aad21d2459-im-bot` |

---

## 目录结构

```
quyou-monitor/
├── SKILL.md
└── scripts/
    ├── scan.py           # 全量城市异步并发扫描，输出 markdown 到 stdout + latest.json
    ├── run_scan.sh       # Shell 包装：执行 scan.py
    └── send_report.py    # 读取 latest.json 并通过 OpenClaw 推送微信
```

---

## 脚本说明

### scan.py

- **并发数**：15个并发请求，超时12秒/次
- **城市码表**：完整国内城市（含县级市/自治州/盟）→ `NAME_TO_CODE` 字典
- **去重逻辑**：按城市对（ori, des, date）去重，北京航线单独显示往返状态
- **输出格式**：
  - 上海↔北京：每周末单独一行显示去程✅/❌ + 返程✅/❌
  - 其他城市：分 `往返完整` / `仅去程` / `仅返程` 三类
  - 完整周末（周六+周日连续）合并为一个周末组
- **输出文件**：`/root/.openclaw/workspace/flight_monitor/latest.json`（JSON格式，含 `time` 和 `msg` 字段）

### run_scan.sh

```bash
cd /root/.openclaw/workspace/flight_monitor
python3 scan.py
```

### send_report.py

读取 `latest.json` 的 `msg` 字段，通过 OpenClaw `message` 工具发送到微信（自动分割长消息，每段≤1800字符）。

---

## Cron 配置

当前已配置的 cron 任务：

| 名称 | 触发时间 | Job ID |
|---|---|---|
| 机票日报推送 | 每天 22:00（上海时区） | `4afd0c55-1f1c-4b33-a6e0-08bb41542dda` |

**链路**：
1. cron 触发 isolated agent
2. agent 执行 scan.py（通过 run_scan.sh）
3. scan.py 写入 latest.json
4. cron 的 delivery announce 读取 latest.json msg 并推微信

**注意**：cron 任务的 delivery 使用 `announce` 模式推送到 `openclaw-weixin:o9cq80z7kiH3T89SkFejq__GHBIg@im.wechat`（注意 chat_id 后缀 `@im.wechat`）。当前账号为 `42aad21d2459-im-bot`。

---

## 常见问题排查

### 最新报告日期不是今天

检查 scan.py 是否正常运行：
```bash
cd /root/.openclaw/workspace/flight_monitor
python3 scan.py 2>&1 | tail -20
cat latest.json | python3 -c "import sys,json; print(json.load(sys.stdin)['time'][:10])"
```

### 推送失败（Outbound not configured）

当前 cron 已连续失败，根因是 `openclaw-weixin` 频道的 `accountId` 配置不一致：
- cron delivery 中配置的 accountId：`42aad21d2459-im-bot`
- 实际可用的 accountId：需确认为 `68b0d200b716-im-bot`（同 push_report.sh 中使用的）

**修复方案**：更新 cron job 的 delivery accountId，或者重建 cron 任务。

### 有票但未出现在报告中

检查 `NAME_TO_CODE` 是否包含该城市。可能原因：
- 城市名不匹配（如 "呼伦贝尔" vs "呼伦贝尔市"）
- 城市码表未收录（如某些县级市）

---

## 更新记录

- **2026-05-27**：从 workspace/flight_monitor/ 迁移为独立 skill
- **2026-05-26**：全量城市扫描上线，city_code_map 扩充至80+城市
- **2026-05-24**：cron 配置重建（脚本路径+参数问题修复）
- **2026-05-21**：首次确认 06/06 起出行模式中断