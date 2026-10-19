<div align="center">

# MICA

**Multiagent Information Coordination Architecture**

面向异构智能体团队的任务导向语义通信实验平台

[![CI](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml/badge.svg)](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

[English](README.md) · **简体中文**

[开始使用](#开始使用) · [项目结构](#项目结构) · [实验结果](#实验结果) · [图表目录](reports/current/README.md)

</div>

**当前主基线已完成：**三个 planner + 三个不同模型 LLM，共 1380 次任务，后端回退为零。[结果与 Table XII](reports/current_mixed/README.md) · [中英文图表](reports/current_mixed/FIGURES.md)。



## 当前主基线：3 个 planner + 3 个不同模型的 LLM

每次任务的 0、2、4 号智能体分别使用 `qwen3:8b`、`llama3.1:8b`、`gemma3:12b`，其余三个使用 planner。完整主实验统一使用当前 EToM 和精确 DP 调度器。团队规模扫描固定这三个 LLM，改变 planner 数量，总规模为 6、8、10、12、14。

```bash
python -m experiments.run_current --table-xii --seeds 12 --workers 6 --output results/current_mixed_20261019
python -m experiments.summarize_current --input results/current_mixed_20261019
```

完整矩阵为 112 个配置单元，另加 3 个 Table XII 正交链路对照单元；每单元 12 个相同任务种子，共 1,380 次任务。Table XII 对照使用每 agent 每时隙 100 个符号；主搜索实验使用总计 300 个符号的共享上行和静态均分。三模型混编是对论文团队结构的扩展，模型版本与论文不同，不能声称复现论文原始数值。

结果自动导出 `missions.jsonl`、`manifest.json`、`summary.json`、`metrics.csv`、`README.md`，包含逐 agent 模型身份、LLM 回退检查、配对时间差、通信比值和 95% bootstrap 区间。后端回退会中止对应任务，不会作为有效结果记录。相同命令支持断点续跑，代码、配置、模型摘要和种子必须一致。`mica-mission` 默认也使用三模型混编；纯 planner 诊断需显式指定 `--team planner`。

下方纯 planner 和单模型 LLM 结果均为历史快照。

---

## 项目概述

MICA 在网格点位搜救任务中研究：**传什么语义、何时值得通信、如何分配有限信道资源**。智能体利用局部观测寻找隐藏目标，交换确认、观测证据与搜索意图；通信会影响团队后续的搜索决策。

当前可执行任务使用任务价值调度器，预测消息对队友搜索效用的影响，结合投递成功率和符号成本选择消息与速率。智能体支持经典规划器和 Ollama 本地 LLM。`demand/` 中的按需证据交互组件仍在协议验证阶段，尚未接入完整任务闭环。

## 开始使用

在 WSL 中使用已有 Python 环境即可；首次安装本项目的可编辑包：

```bash
python -m pip install -e ".[dev]"
mica-mission --scheme mica --seed 9000
python -m pytest -q
```

默认任务使用三个不同模型的混编团队，需要 Ollama。纯 planner 诊断请显式指定 `mica-mission --team planner`。从 WSL 无法访问 Windows localhost 时，将端点地址替换为 Windows 主机地址。

```bash
python -m experiments.run_team_benchmark --help
python -m experiments.run_team_benchmark --url http://localhost:11434 \
  --seeds 12 --output results/team_new
```

模型为 `qwen3:8b`、`llama3.1:8b`、`gemma3:12b`。默认每次任务混编三个不同模型各一个智能体和三个 planner。历史单模型团队比较需显式指定 `--team-mode single_model`。

## 项目结构

```text
mica-comm/
├── src/mica_comm/
│   ├── core/              # 配置、路径、代码指纹
│   ├── world/             # 网格环境、信念、救援任务
│   ├── agents/            # 规划器、LLM 接口、队友行为预测
│   ├── communication/     # 消息、链路、调度与联合选择
│   ├── simulation/        # 任务闭环、广播与资源统计
│   ├── demand/            # 按需协议组件，尚未接入任务闭环
│   ├── evaluation/        # 实验队列与配置校验
│   └── visualization/     # 图表样式、字体与中英文支持
├── experiments/           # 实验入口与分析
├── scripts/               # 数据导入、缓存核验工具
├── tests/                 # 行为、协议与结果完整性测试
├── reports/current/       # 结果快照、统计与图表索引
├── figures/current/       # 中英文 PDF、SVG、PNG 图表
└── results/               # 本地日志与缓存，Git 忽略
```

`src` 保留统一的 `mica_comm` 包名，内部按职责分层。可复用的任务与通信逻辑放入对应子包，实验入口负责参数和编排。公共接口示例：

```python
from mica_comm import Config, run_episode

config = Config().with_(grid=32, n_agents=6, symbols_per_slot=100)
result = run_episode(config, "mica", seed=9000)
```

## 实验结果

### 经典规划团队

2026-10-19 在 WSL 运行 **1,272 次任务**：106 个配置单元，每单元使用相同的 12 个种子（9000–9011）。默认 $32\\times32$ 网格、6 个智能体、8 个隐藏目标、100 符号/智能体/时隙，参考 SNR 为 5 dB，上限 400 时隙。

| 通信策略 | 完成时长 / 时隙 | 上行符号用量 | 总符号用量 | 完成率 |
| --- | ---: | ---: | ---: | ---: |
| 定时状态共享（SYNC） | 82.25 | 43,407.83 | 49,734.17 | 100% |
| 任务价值调度（MICA） | 65.25 | 11,509.25 | 14,658.08 | 100% |
| 即时共享参考（IDEAL） | 68.17 | — | — | 100% |

IDEAL 绕过上行投递约束，其零上行记账不代表实际零成本。总符号用量包含上行数据、请求、广播、反馈和授权。逐任务结果见 [metrics.csv](reports/current/metrics.csv)，配置见 [manifest.json](reports/current/manifest.json)。

![任务完成时长与上行开销](reports/current/previews/zh_standard.png)

### 异构 LLM 团队

以下 108 次任务于 2026-10-18 在线生成模型响应。本轮用我们自己的缓存回放，逐条核验重构后的任务指标一致，未发起新推理请求。每个模型、每个策略使用 12 个种子（8000–8011），全部任务完成且没有后端回退。

| 模型 | SYNC 时长 | MICA 时长 | IDEAL 时长 | SYNC 上行符号 | MICA 上行符号 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 8B | 80.58 | 89.83 | 73.92 | 41,115.25 | 15,687.00 |
| Llama 3.1 8B | 93.83 | 90.75 | 88.58 | 48,761.83 | 15,094.08 |
| Gemma 3 12B | 120.92 | 85.00 | 62.25 | 64,759.17 | 13,837.67 |

时长均为**仿真时隙**，不是模型推理秒数。Gemma 为 12B，另两个为 8B；这些结果不能证明参数规模或推理计算效率的优劣。完整区间与同种子差异见 [LLM 统计](reports/current/llm/summary.json)。

![语言模型任务表现与上行开销](reports/current/previews/zh_llm.png)

## 图表与复现

[18 个图表主题的中英文目录](reports/current/README.md)涵盖任务时长与开销、目标进度、团队规模、预算、信噪比、广播可靠性、共享预算、有限码长、限时救援、资源权衡、模块分析、搜索轨迹、模型差异与价值扰动。中文文件按内容命名，例如 `15_多智能体搜索轨迹.pdf`。

仓库提供带代码指纹的结果快照和最终矢量图表。绘图实现作为内部工具保留，不纳入公开源码。若要为后续研究重新运行经典规划实验：

```bash
python -m experiments.run_current --table-xii --seeds 12 --workers 6 --output results/current_mixed_new
```

发布图表中的阴影与误差线为按任务种子重采样的探索性 95% bootstrap 区间，未校正多重比较；未完成任务保留上限时长，不从统计删除。图 13 为预算点的均值权衡，不宣称全局 Pareto 最优；轨迹图固定使用首个种子。

旧本地图表保存在 `results/figure_archive_20261019/`。
