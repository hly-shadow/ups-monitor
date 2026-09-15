# Raspberry Pi UPS Monitor

用于 Raspberry Pi 的 UPS 断电检测和安全关机程序。

## 功能

- 检测 UPS 电源状态
- 断电信号持续 2 秒才确认断电
- 2 秒内恢复供电则取消关机
- 持续断电则执行：
  1. sync
  2. 等待 1 秒
  3. shutdown -h now
- 支持系统启动时已经处于断电状态
- 使用 Git 进行版本管理
- 使用 systemd 作为后台服务运行

## 注意：

- 运行用户需要具备sudo权限，最好配置无密码sudo
- 需安装gpiozero库：`pip3 install gpiozero`

## 状态机
             GPIO active
                  │
                  ▼
          ┌───────────────┐
          │ power_loss    │
          │ detected      │
          └───────┬───────┘
                  │
             start Timer
                  │
          ┌───────┴────────┐
          │                │
      < 2 seconds       >= 2 seconds
          │                │
    GPIO restored          ▼
          │          shutdown_requested
          ▼                │
       CANCEL              ▼
                       sync + shutdown

## 项目结构

```text
ups_monitor/
├── main.py
├── config.py
├── logger.py
├── system.py
├── monitor.py
├── requirements.txt
├── README.md
├── .gitignore
├── logs/
├── systemd/
│   └── ups-monitor.service