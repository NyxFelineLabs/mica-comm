<div align="center">

# MICA

**Multiagent Information Coordination Architecture**

面向异构智能体团队的语义通信与协作实验平台。

[![CI](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml/badge.svg)](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-16866A)](LICENSE)

[English](README.md) · **简体中文**

[快速开始](#快速开始) · [实验运行](#实验运行) · [实验结果](#实验结果) · [文档导航](#文档导航)

</div>

---

## 项目概览

MICA 研究无线资源受限时，智能体应该**传什么、何时传、以什么速率传**。
平台以搜索救援任务为载体，将局部感知、共享信念、传统规划器或 LLM 规划器，
以及面向任务价值的消息调度整合进可复现的仿真流程。

| 层次 | 支持内容 |
| --- | --- |
| 智能体团队 | 传统规划器与可选的 Ollama 本地 LLM 智能体 |
| 通信机制 | 证据、意图、确认消息、衰落信道与传输速率选择 |
| 实验评估 | 固定随机种子、基线、消融、独立测试集校准与资源统计 |

```mermaid
flowchart LR
    A[局部感知] --> B[信念更新与规划]
    B --> C[MICA 消息调度]
    C --> D[无线上行传输]
    D --> E[边缘融合与广播]
    E --> F[移动与任务推进]
    F --> A
```

项目与方法统一称为 **MICA**。GitHub 仓库和 Python 发行包名为 `mica-comm`，
Python 导入包名为 `mica_comm`，主要通信策略 ID 为 `mica`。

## 快速开始

需要 Python 3.9 或更新版本。默认任务不需要 LLM 服务或 GPU。

```bash
git clone https://github.com/NyxFelineLabs/mica-comm.git
cd mica-comm
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m mica_comm.simulator --scheme mica --seed 0
```

Windows PowerShell 使用 `.\.venv\Scripts\Activate.ps1` 激活环境。
已有可用环境时，可以跳过环境创建，直接用该环境的 Python 安装项目。

默认 seed-0 任务应在 **122 个时隙**完成，使用 **13,304 个上行符号**。
这两个数值用于软件回归检查，不代表性能优势。
安装后的 `mica-mission --scheme mica --seed 0` 命令与上述运行方式等价。

<details>
<summary><strong>Python 调用示例</strong></summary>

```python
from mica_comm import Config, run_episode

config = Config().with_(symbols_per_slot=50)
result = run_episode(config, scheme="mica", seed=0)
print(result["completion_time"], result["symbols"])
```

</details>

## 实验运行

激活环境后，在仓库根目录运行以下命令。

| 实验目的 | 命令 |
| --- | --- |
| 基线小规模检查 | `python -m experiments.run_all --only default --seeds 2` |
| 通信模块消融 | `python -m experiments.run_robustness --only ablation --seeds 2` |
| 传统规划器的队友行为校准 | `python -m experiments.run_behavior_calibration --train-seeds 16 --eval-seeds 30 --workers 4` |
| LLM 团队的队友行为校准 | `python -m experiments.run_llm_calibration --models qwen3:8b llama3.1:8b` |

LLM 校准实验要求 Ollama 已安装上述两个模型。脚本使用独立训练种子拟合参数，
冻结后在测试种子上比较**同一个模型下的原版与校准版 softmax**。
每个团队由 3 个 LLM 智能体和 3 个传统规划器组成；出现模型调用回退时，实验会停止。

WSL 调用 Windows Ollama 的方法见 [LLM 实验协议](docs/llm_behavior_calibration.md)，
其中包含使用已有 Windows Python 的桥接方式。通用客户端通过 `MICA_OLLAMA_URL`
接收完整的 `/api/generate` 地址；校准脚本的 `--url` 参数则接收服务基础地址。
模型别名和缓存说明见 [模型后端](docs/model_backends.md)。

实验产物保存在本地，不进入 Git：

```text
results/    逐种子记录、汇总、冻结的校准参数与 LLM 响应缓存
figures/    生成的分析图表
```

可以用 `MICA_RESULTS_DIR`、`MICA_FIGURES_DIR` 和 `MICA_CACHE_DIR` 重定向标准输出目录。
比较策略时须使用相同配置与种子集合，并区分仿真时隙和实际推理耗时。

## 实验结果

> **当前结论：** softmax 校准在已测试的 LLM 团队中减少了通信量，
> 但尚未证明整体效率提升，因此默认不启用。

下表相对**同一模型的原版 softmax**计算，每个场景使用 12 对测试种子。
完成时隙增加表示任务变慢。96 次评估任务全部完成，模型调用回退为零。

| 模型 | 场景 | 平均上行符号数 | 平均完成时隙 |
| --- | --- | ---: | ---: |
| Qwen3 8B | 默认分布 | −23.6% | +23.2% |
| Qwen3 8B | 聚集分布 | −28.5% | +19.2% |
| Llama 3.1 8B | 默认分布 | −35.5% | +33.0% |
| Llama 3.1 8B | 聚集分布 | −40.7% | +10.6% |

这些是探索性实验的均值，不能解释为四组均已在统计上证实变慢。
Llama 默认场景的时隙差区间不包含零，其余三组包含零。
配对置信区间、预测诊断、缓存统计与局限见 [LLM 完整报告](docs/llm_behavior_calibration_results.md)；
传统规划器实验见 [独立实验报告](docs/behavior_calibration_results.md)。
缓存回放耗时不能作为在线推理加速的证据。

## 项目结构

```text
mica-comm/
├── src/mica_comm/       仿真器、规划器、信道、消息与 MICA 调度器
├── experiments/         实验运行、分析与绘图
├── scripts/             单项任务与缓存工具
├── tests/               单元测试与回归测试
├── docs/                架构、实验协议与实测结果
└── .github/workflows/   持续集成
```

可复用方法放在 `src/mica_comm/`，实验组织放在 `experiments/`。
模型响应和生成的任务记录不提交到仓库。

## 文档导航

以下详细文档目前使用英文。

| 文档 | 内容 |
| --- | --- |
| [项目架构](docs/architecture.md) | 仿真流程、模块划分与扩展入口 |
| [实验工作流](docs/experiments.md) | 参数扫描、策略 ID、公平对比与输出约定 |
| [模型后端](docs/model_backends.md) | Ollama、模型别名与响应缓存 |
| [行为模型校准](docs/behavior_calibration.md) | 队友 softmax 参数拟合与假设 |
| [LLM 校准协议](docs/llm_behavior_calibration.md) | 独立测试集评估与 Windows/WSL 推理 |
| [贡献指南](CONTRIBUTING.md) | 开发约定与检查命令 |

开发检查：

```bash
black --check src tests experiments scripts
ruff check src tests experiments scripts
python -m pytest -q
```

**已有工作副本升级：** Python 导入、命令行入口和项目环境变量现统一为
`mica_comm`、`mica-mission` 和 `MICA_`。请重新执行可编辑安装，并更新 Shell 配置。
已有实验数据会保留；重命名改变了源码哈希，校验源码的实验需要使用新的输出目录。

## 开源许可

采用 MIT 许可证。版权及代码来源见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE.md)。
发表实验结果时，请记录代码版本、配置、模型摘要与种子集合。
