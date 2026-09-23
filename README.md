# Raspberry Pi UPS Monitor

用于 Raspberry Pi 的 UPS 断电检测和安全关机程序。

## 功能

- 读取UPS电池容量、输出电压，判断外部电源是否断开
- 输出电压降到指定值，执行关机操作
- 记录日志


## 注意：

- 运行程序的用户需具备sudo权限
- 暂时满足个人使用
- 安装依赖：`pip install -r requirements.txt`

## 状态机
```text
                 UPS                     UART
                  │                       │
        ┌─────────┴─────────┐             ├──Vin GOOD/NG  ← 判断外部电源
        │                   │             ├──BATCAP 100   ← 电池容量                   
       UART                 STA           └──Vout 5250    ← 输出电压 
        │                   │
 Vin/BATCAP/Vout        厂商 Halt
        │                   │
        ▼                   ▼
  软件提前预警/保护       最终硬件保护
        │                   │
        └────────┬──────────┘
                 ▼
         ShutdownController
                 │
                 ▼
          safe_shutdown() 

```
## 项目结构

```text
ups_monitor/
├── main.py
├── config.py
├── power_monitor.py
├── shutdown_controller.py
├── simulator.py
├── logger.py
├── system.py
├── monitor.py
├── ups_uart.py
├── requirements.txt
├── README.md
├── .gitignore
├── logs/
├── test.py
├── systemd/
│   └── ups-monitor.service
└─
```
## UPS 开发板输出信息
```text
b' $ SmartUPS V3.2P,Vin GOOD,BATCAP 100,Vout 5250 $'
```
- Vin GOOD  = 外部输入电源正常
- Vin NG    = 外部输入电源断开

## 连接图

| 图片 | 描述 |
| :---: | :---: |
| <img src="https://picgocloud.com/m/2f846afd-1772-4a2e-9613-71761aac5ef8.jpeg" width="200" />| UPS开发板图片 |
| <img src="https://picgocloud.com/m/c79c09c7-87a3-4004-95b9-49050aa133ba.jpg" width="200" /> | 接线示意图,将UPS开发板上的RX TX接到树莓派主板上,STA接到树莓派任意一个GPIO引脚(本程序使用GPIO17);UPS开发板5V/GND或者USB对树莓派供电二选一即可|
| <img src="https://picgocloud.com/m/8cf96c09-4c21-4bff-8042-434ea39578b3.jpeg" width="200" />| 最终成果 |

## 其它

### UPS开发板介绍

- 自动关机:当外部电源适配器停电,UPS自动采用电池作为后备电源对树莓派进行供电;当电池即
将耗尽之前,UPS主板会通过System haltsignal通知树莓派提前关机.然后UPS主板会自动切断树莓
派主电源,并且UPS自动进入睡眠模式,等待外部供电恢复.
- 自动开机:当外部供电恢复后,UPS主板会自动恢复运行,并且开始对电池进行充电.经过一段时间
充电后,UPS主板会自动打开树莓派的主供电电源,从而让树莓派恢复运行状态。
- 商家提供的资料有限,并且当达到UPS内置关机条件时,树莓派已经出现电压不足,并且散热风扇已经
无法正常工作,所以暂时通过python程序来关机.