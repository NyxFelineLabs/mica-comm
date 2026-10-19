# Current mixed-team figure collection

主基线：3 个 planner + Qwen3 8B、Llama 3.1 8B、Gemma 3 12B 各一个 LLM agent。

完整校验 1380 次任务；后端回退 0 次。

[统计与 Table XII 格式结果](README.md) · [逐任务指标](metrics.csv)

图中区间为按任务种子重采样的探索性 95% bootstrap 区间，未校正多重比较。轨迹固定使用首个种子。预算散点为均值，不代表全局 Pareto 最优。

## zh

| 图表 | PDF | SVG |
| --- | --- | --- |
| 三个 planner + 三个不同模型 LLM | [PDF](../../figures/current_mixed/zh/01_primary.pdf) | [SVG](../../figures/current_mixed/zh/svg/01_primary.svg) |
| 搜索进度 | [PDF](../../figures/current_mixed/zh/02_progress.pdf) | [SVG](../../figures/current_mixed/zh/svg/02_progress.svg) |
| 团队规模 | [PDF](../../figures/current_mixed/zh/03_team_size.pdf) | [SVG](../../figures/current_mixed/zh/svg/03_team_size.svg) |
| 静态共享上行预算 | [PDF](../../figures/current_mixed/zh/04_budget.pdf) | [SVG](../../figures/current_mixed/zh/svg/04_budget.svg) |
| SNR 与任务时长 | [PDF](../../figures/current_mixed/zh/05_snr_time.pdf) | [SVG](../../figures/current_mixed/zh/svg/05_snr_time.svg) |
| SNR 与通信开销 | [PDF](../../figures/current_mixed/zh/06_snr_cost.pdf) | [SVG](../../figures/current_mixed/zh/svg/06_snr_cost.svg) |
| 配对时长差：正值表示 MICA 更快 | [PDF](../../figures/current_mixed/zh/07_paired_snr.pdf) | [SVG](../../figures/current_mixed/zh/svg/07_paired_snr.svg) |
| 广播丢失 | [PDF](../../figures/current_mixed/zh/08_broadcast_loss.pdf) | [SVG](../../figures/current_mixed/zh/svg/08_broadcast_loss.svg) |
| 广播延迟 | [PDF](../../figures/current_mixed/zh/09_broadcast_delay.pdf) | [SVG](../../figures/current_mixed/zh/svg/09_broadcast_delay.svg) |
| 价格协调的共享上行 | [PDF](../../figures/current_mixed/zh/10_shared_budget.pdf) | [SVG](../../figures/current_mixed/zh/svg/10_shared_budget.svg) |
| 有限码长信道 | [PDF](../../figures/current_mixed/zh/11_finite_blocklength.pdf) | [SVG](../../figures/current_mixed/zh/svg/11_finite_blocklength.svg) |
| 截止时间前救援 | [PDF](../../figures/current_mixed/zh/12_rescue.pdf) | [SVG](../../figures/current_mixed/zh/svg/12_rescue.svg) |
| 预算点均值：标注为每 agent 符号份额 | [PDF](../../figures/current_mixed/zh/13_budget_tradeoff.pdf) | [SVG](../../figures/current_mixed/zh/svg/13_budget_tradeoff.svg) |
| 调度器消融 | [PDF](../../figures/current_mixed/zh/14_components.pdf) | [SVG](../../figures/current_mixed/zh/svg/14_components.svg) |
| MICA 轨迹，种子 9000 | [PDF](../../figures/current_mixed/zh/15_trajectory.pdf) | [SVG](../../figures/current_mixed/zh/svg/15_trajectory.svg) |
| Table XII 扩展：三个模型在同一团队 | [PDF](../../figures/current_mixed/zh/16_table_xii.pdf) | [SVG](../../figures/current_mixed/zh/svg/16_table_xii.svg) |
| 混编团队内的模型行为 | [PDF](../../figures/current_mixed/zh/17_agent_behavior.pdf) | [SVG](../../figures/current_mixed/zh/svg/17_agent_behavior.svg) |
| 语义价值噪声 | [PDF](../../figures/current_mixed/zh/18_value_noise.pdf) | [SVG](../../figures/current_mixed/zh/svg/18_value_noise.svg) |
| 上行协调模式 | [PDF](../../figures/current_mixed/zh/19_coordinator.pdf) | [SVG](../../figures/current_mixed/zh/svg/19_coordinator.svg) |

## en

| 图表 | PDF | SVG |
| --- | --- | --- |
| Three planners + three different LLMs | [PDF](../../figures/current_mixed/en/01_primary.pdf) | [SVG](../../figures/current_mixed/en/svg/01_primary.svg) |
| Search progress | [PDF](../../figures/current_mixed/en/02_progress.pdf) | [SVG](../../figures/current_mixed/en/svg/02_progress.svg) |
| Team size | [PDF](../../figures/current_mixed/en/03_team_size.pdf) | [SVG](../../figures/current_mixed/en/svg/03_team_size.svg) |
| Static shared uplink budget | [PDF](../../figures/current_mixed/en/04_budget.pdf) | [SVG](../../figures/current_mixed/en/svg/04_budget.svg) |
| SNR and mission time | [PDF](../../figures/current_mixed/en/05_snr_time.pdf) | [SVG](../../figures/current_mixed/en/svg/05_snr_time.svg) |
| SNR and communication cost | [PDF](../../figures/current_mixed/en/06_snr_cost.pdf) | [SVG](../../figures/current_mixed/en/svg/06_snr_cost.svg) |
| Paired time differences; positive favors MICA | [PDF](../../figures/current_mixed/en/07_paired_snr.pdf) | [SVG](../../figures/current_mixed/en/svg/07_paired_snr.svg) |
| Broadcast loss | [PDF](../../figures/current_mixed/en/08_broadcast_loss.pdf) | [SVG](../../figures/current_mixed/en/svg/08_broadcast_loss.svg) |
| Broadcast delay | [PDF](../../figures/current_mixed/en/09_broadcast_delay.pdf) | [SVG](../../figures/current_mixed/en/svg/09_broadcast_delay.svg) |
| Price-coordinated shared uplink | [PDF](../../figures/current_mixed/en/10_shared_budget.pdf) | [SVG](../../figures/current_mixed/en/svg/10_shared_budget.svg) |
| Finite-blocklength channel | [PDF](../../figures/current_mixed/en/11_finite_blocklength.pdf) | [SVG](../../figures/current_mixed/en/svg/11_finite_blocklength.svg) |
| Rescue before deadlines | [PDF](../../figures/current_mixed/en/12_rescue.pdf) | [SVG](../../figures/current_mixed/en/svg/12_rescue.svg) |
| Budget means; labels are per-agent symbol shares | [PDF](../../figures/current_mixed/en/13_budget_tradeoff.pdf) | [SVG](../../figures/current_mixed/en/svg/13_budget_tradeoff.svg) |
| Scheduler ablations | [PDF](../../figures/current_mixed/en/14_components.pdf) | [SVG](../../figures/current_mixed/en/svg/14_components.svg) |
| MICA trajectory, seed 9000 | [PDF](../../figures/current_mixed/en/15_trajectory.pdf) | [SVG](../../figures/current_mixed/en/svg/15_trajectory.svg) |
| Table XII extension: three models in one team | [PDF](../../figures/current_mixed/en/16_table_xii.pdf) | [SVG](../../figures/current_mixed/en/svg/16_table_xii.svg) |
| Model behavior within the mixed team | [PDF](../../figures/current_mixed/en/17_agent_behavior.pdf) | [SVG](../../figures/current_mixed/en/svg/17_agent_behavior.svg) |
| Semantic value noise | [PDF](../../figures/current_mixed/en/18_value_noise.pdf) | [SVG](../../figures/current_mixed/en/svg/18_value_noise.svg) |
| Uplink coordination modes | [PDF](../../figures/current_mixed/en/19_coordinator.pdf) | [SVG](../../figures/current_mixed/en/svg/19_coordinator.svg) |
