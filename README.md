# Raspberry Pi UPS Monitor

用于 Raspberry Pi 的 UPS 断电检测和安全关机程序。

## 功能

```text
  外部电源断开
        ↓
  UPS继续用电池供电
        ↓
  电池接近耗尽
        ↓
  UPS发送 STA/Halt 脉冲
        ↓
  GPIO17 检测到 HIGH
        ↓
  HIGH 持续约 2~3 秒
        ↓
  安全关机
```

## 注意：

- 运行用户需要具备sudo权限，最好配置无密码sudo
- 需安装gpiozero库：`pip3 install gpiozero`

## 状态机
```text
             UPS                UART
              │                  │
       ┌──────┴──────┐           ├── Vin GOOD / NG       ← 判断外部电源
       │             │           ├── BATCAP 100          ← 电池容量
      UART          STA          └── Vout 5250           ← 输出电压
       │             │
       ▼             ▼          GPIO17 / STA
 Vin GOOD/NG       GPIO17        │
       │             │           └── Halt signal         ← UPS要求Pi关机
       └──────┬──────┘
              ▼
        UPSMonitor
              │
              ▼
       安全关机状态机
              │
              ▼
       sync + shutdown   

```
## 项目结构

```text
ups_monitor/
├── main.py
├── config.py
├── logger.py
├── system.py
├── monitor.py
├── ups_uart.py
├── requirements.txt
├── README.md
├── .gitignore
├── logs/
├── systemd/
│   └── ups-monitor.service
└─
```
## UPS 开发板输出信息
```text
b' $ SmartUPS V3.2P,Vin GOOD,BATCAP 100,Vout 5250 $'

Vin GOOD  = 外部输入电源正常
Vin NG    = 外部输入电源断开