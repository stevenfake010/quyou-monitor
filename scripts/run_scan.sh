#!/bin/bash
# 每日机票扫描脚本
# 输出到 /root/.openclaw/workspace/flight_monitor/latest_report.txt

cd /root/.openclaw/workspace/flight_monitor
python3 scan.py > /root/.openclaw/workspace/flight_monitor/latest_report.txt 2>&1
echo "Exit code: $?" >> /root/.openclaw/workspace/flight_monitor/latest_report.txt
