# 面向异构智能体团队的资源高效任务导向语义通信

**Resource-Efficient Task-Oriented Semantic Communication for Heterogeneous Agent Teams**

## 摘要

本文的核心问题是：在部分可观测、异构智能体和有限无线资源同时存在时，如何判断“什么信息值得传输”，并以尽可能低的通信代价改变团队行为、提高搜索与救援效率。

多智能体搜索与救援系统需要在局部观测、分散决策和受限无线链路之间形成闭环。经典规划器与大语言模型（large language model，LLM）智能体的决策接口不同，固定周期报告又无法区分消息对任务进展的实际作用。本文提出一个五层端到端系统：环境与信念状态、异构智能体决策、语义消息与价值估计、无线资源调度与传输、仿真与统计评估。系统以 EVID、CONF 和 INTENT 作为统一消息协议，使三个经典规划器和三个不同模型的 LLM agent 能够在相同信道与调度器中协作。EToM（Efficient Theory-of-Mind）被放置在价值估计层，用于预测消息到达后队友行动效用的变化；它可以与信息增益、公共任务相关性、信息年龄和负载等规则互换。调度器将语义价值、链路成功概率、速率和符号成本联合起来，并用逐时隙的多组选择动态规划处理离散预算。针对估值中的重复几何运算，本文实现快照内缓存和前后缀分解，并检查数值、排序、调度和完整任务输出是否保持一致。

在纯 Planner 的匹配成本实验中，目标为每任务 5,000、10,000 和 20,000 个上下行总符号。成本标准化后，EToM 的平均完成时隙分别为 82.3、71.6 和 67.4；在 5,000 和 10,000 符号点，相对于部分替代价值规则的配对差异区间不跨零，而在 20,000 符号点没有明确优势。32×32 网格、6 个 agent、8 个证据前缀的计算基准中，历史实现与缓存加分解实现的配对加速为 1.31 [1.27, 1.33] 倍，最大估值误差约为 1.14×10^-16，80 对完整任务的调度和任务输出保持一致。三 Planner 加 Qwen3、Llama 3.1、Gemma 3 的混合 campaign 完整运行 1,380/1,380 个任务且无 LLM fallback。Table XII 正交上行扩展中，MICA 平均完成 83.08 个仿真时隙、使用 12,924.25 个上行符号，SEM 分别为 91.75 和 47,989.75；共享 300 symbols/slot 的静态均分设置中，MICA 使用 8,685.83 个上行符号，但平均完成时间 108.50 个时隙，高于 SEM 的 90.50 个时隙。结果说明 MICA 在给定场景下能显著减少上行符号，但任务时延取决于共享资源和信道条件，不能由通信节省直接推出全面的任务性能优势。

**关键词：** 任务导向语义通信；异构多智能体；接收者价值估计；无线资源调度；多智能体搜索与救援

## 0 引言

机器人、无人机和基于 LLM 的软件智能体被用于协同搜索、巡检和灾害响应。每个参与者只能看到局部区域，并可能采用不同的目标选择机制。团队需要交换传感器证据、目标确认和行动意图，同时面对路径损耗、衰落、丢包、广播延迟和多发送端竞争。通信策略因此需要同时回答三个问题：发送什么、什么时候发送，以及在有限符号预算下为哪些消息提供可靠传输。

逐比特传输、固定周期报告和单纯按 payload 排序无法表达消息的任务差异。相同大小的两条证据可能使队友采取完全不同的行动；新鲜但不改变搜索目标的状态也不一定值得立即发送。消息价值估计还需要考虑成功投递概率和速率带来的符号成本。如果价值模型对每个接收者和每个候选重复构造空间几何，通信决策本身会成为计算瓶颈。

本文围绕三个挑战展开：

1. **消息价值依赖接收者行为。** 消息的价值不等于 belief 变化或 bits 数量，而取决于它是否改变队友后续目标、空间分工或救援认领；发送者还只能看到不完整的公共状态。
2. **语义价值与无线传输耦合。** 消息内容、传输速率、链路可靠性、包开销和共享预算必须共同决定发送选择，单独优化信息量或固定周期会浪费符号。
3. **异构团队需要统一且可复现的协作接口。** Planner、Qwen3、Llama 3.1 和 Gemma 3 的行为分布、输出稳定性和推理后端不同，必须在同一协议、信道和 seed cohort 下运行，才能把模型差异与通信机制区分开。

对应地，本文给出三项创新设计：

1. **EToM 行为价值估计。** 只使用发送者可见的公共 belief、公开意图和几何状态，反事实预测消息是否会改变接收者的任务行动，并同时评估 evidence 和 intent。
2. **VoI-aware exact scheduler。** 将 EToM 或替代价值、packet success probability、速率、控制开销和共享符号价格放入同一个逐时隙多组选择问题。
3. **统一协议下的可复现混合团队。** 用 EVID、CONF、INTENT 接入 Planner 和多个 LLM，并通过 JSON schema、模型 digest、响应缓存、源代码指纹、matched seeds 和 zero-fallback 记录保证实验可追溯。

本文的实验重点是当前项目中已经运行的三 Planner 加三种不同 LLM 的混合团队。该设置用于验证统一协议和端到端仿真闭环；它不构成三种模型能力相等、异构性因果效应或模型间优劣的证明。所有数值均来自本项目报告，中文参考论文译稿只用于结构和术语参考，不作为本项目实验数据来源。

本文进一步检验三个可证伪假设：H1，在相同通信成本下，行为价值规则比只看 bits、AoI 或一般 belief 增益更能优先发送会改变队友行动的信息；H2，在低 SNR、有限码长、包开销和共享预算下，联合价值、可靠性与资源调度比固定周期策略使用更少通信符号，但任务时延取决于资源模式；H3，统一协议能让异构 Planner-LLM 团队保持可运行和可复现，同时保留模型行为差异供独立分析。

## 1 系统模型与问题定义

### 1.1 搜索与救援环境

搜索区域为 $N\times N$ 网格，单元集合为 $\mathcal C$，$G=N^2$。环境包含 $V$ 个隐藏幸存者，可采用均匀或聚类布局。每个 agent 在离散时隙中移动到相邻网格单元，并在当前位置附近的感知窗口产生带噪观测。搜索任务在所有幸存者被定位后结束；救援任务还为每个幸存者设置截止时间，要求某个 agent 到达后连续服务指定时长。

### 1.2 局部信念与公共状态

对单元 $c$，以对数几率
$$
L(c)=\log\frac{P(c)}{1-P(c)}
$$
表示幸存者存在概率。检测和未检测观测分别通过正、负检测的对数似然比更新信念。协调器维护公共 belief $L_c$，agent $k$ 还保留尚未成功上传的私有增量 $\delta_k$，其局部状态写为
$$
L_k=L_c^{(k)}+\delta_k.
$$
其中 $L_c^{(k)}$ 是该 agent 最近成功接收的公共快照。理想下行时 $L_c^{(k)}=L_c$；下行丢失或延迟时，不同 agent 可能看到不同步的公共状态。局部后验达到确认阈值只产生 CONF 候选，只有上行成功后才并入团队公共 belief。

系统还维护公开位置、公开意图、已经确认的网格单元、救援认领和截止时间。随机源按环境、感知、规划、信道和下行过程拆分，并在实验 manifest 中保存任务种子、代码指纹和模型身份。

### 1.3 Planner 与 LLM 混合团队

经典 Planner 根据局部幸存者概率质量、移动距离和队友排斥项为候选单元评分：
$$
S_k(c)=M_k(c)D_k(c)R_k(c),
$$
其中 $M_k(c)$ 表示候选单元感知窗口内的幸存者概率质量，$D_k(c)$ 是 Manhattan 距离折扣，$R_k(c)$ 根据队友公开位置和意图抑制重复搜索。滞回规则减少无必要的目标切换。

LLM agent 先从 belief 中筛选空间上分离的少量候选，再通过结构化提示接收候选坐标、预期目标质量、移动距离及队友公开位置或意图。模型按 JSON schema 返回候选标签；Ollama 响应按模型和提示键控缓存，解析失败时使用已定义的 fallback。LLM 只负责从有限候选中选择目标，不负责无线发包，也不改变接收端融合规则。

当前混合团队的 agent 0、2、4 分别使用 Qwen3 8B、Llama 3.1 8B、Gemma 3 12B，agent 1、3、5 使用经典 Planner。完整 mixed campaign 包含 1,380 个任务，报告验证 1380/1380 missions，LLM backend fallback 为 0。三种 LLM 混用是实验条件，不等于对模型能力进行了控制。

救援场景中，已定位幸存者转化为带截止时间的任务。可行性约束为
$$
deadline-current\_time-travel\_time-remaining\_service\geq 0.
$$
agent 优先保持仍可行的当前承诺，跳过已由更高优先级 agent 认领的任务，并在可行任务中优先选择 slack 较小者。INTENT 因而既表示搜索目标，也表示救援认领。

### 1.4 语义消息与无线信道

统一消息协议如下。

| 消息 | 主要内容 | 接收端作用 |
|---|---|---|
| EVID | 观测位置、时刻和检测单元 | 对公共 belief 执行贝叶斯融合 |
| CONF | 达到确认标准的网格单元 | 声明已定位目标并创建救援任务 |
| INTENT | 当前目标或救援认领 | 更新公开计划并减少空间或任务重复 |

上行使用基于距离的路径损耗和 Rayleigh block fading。outage 模型的速率成功概率为
$$
P_s(R\mid\bar\gamma)=\exp\left(-\frac{2^R-1}{\bar\gamma}\right),
$$
其中 $\bar\gamma$ 为平均 SNR。有限码长设置使用正态近似误块率并对衰落积分。下行广播可丢失或延迟，并计入广播、ACK、请求和授权等控制开销。Genie 直接交付更新，不经过真实上行，因此其上行符号为零只是理想参考，不能解释为部署系统的零通信成本。

### 1.5 优化目标与指标边界

给定每时隙可用符号预算、候选消息和链路状态，系统希望减少上行及上下行总通信符号，同时维持搜索完成时间或救援表现。本文严格区分任务完成时间（仿真时隙）、上行符号、按实验口径计入控制与广播的总通信符号，以及价值估计或完整仿真的计算墙钟。这些指标不互相替代。本文求解的是给定当前有限候选集合的逐时隙选择，不声称得到跨所有时隙的全局最优策略。

## 2 LLM 混合团队的价值估计与通信调度

### 2.1 统一消息接口和候选生成

每个 agent 在一个时隙内依次执行感知、目标决策和消息准备。新证据首先经过相关性过滤：若其在已有排队证据基础上对公共 belief 的期望幸存者质量影响小于阈值 $\varepsilon$，则不进入发送队列。其余证据按时间前缀构成不同聚合长度的 EVID 候选；CONF 和 INTENT 分别形成候选组。

每个传输选项记录 $(m,r,b_m,n_{m,r},v_m)$，其中 $m$ 是消息，$r$ 是速率，$b_m$ 是有效载荷 bits，$n_{m,r}$ 是符号数，$v_m$ 是语义价值。带固定包头 $H$ 时，
$$
n_{m,r}=\left\lceil\frac{b_m+H}{r}\right\rceil.
$$
该接口使 Planner 和 LLM 的认知决策可以独立替换，而不改变消息编码、信道或调度器。

### 2.2 EToM 接收者价值

EToM 将接收者近似为 Boltzmann-rational 搜索者。对公共知识 $K$，接收者 $j$ 选择单元 $c$ 的概率为
$$
\pi_j(c\mid K)=\frac{\exp((S_j(c;K)-M_j)/(\tau_jM_j))}
{\sum_{c'\in\mathcal C}\exp((S_j(c';K)-M_j)/(\tau_jM_j))},
\quad M_j=\max_cS_j(c;K)>0.
$$
当 $M_j\leq0$ 时，期望效用定义为零。对发送者 $k$ 的消息 $m$，EToM 估计其对其他接收者行动效用的变化：
$$
V_k(m)=\sum_{j\ne k}\left[
\mathbb E_{c\sim\pi_j(\cdot\mid K\oplus m)}U_{k,j}(c)-
\mathbb E_{c\sim\pi_j(\cdot\mid K)}U_{k,j}(c)
\right].
$$
接收者策略只使用发送者可见的公共状态，不读取队友私有证据；发送者效用使用其本地 belief。该定义使 EToM 成为消息价值估计模块，而不是 Planner 或 LLM 的目标选择器，也不是整个系统的同义词。

### 2.3 可替换价值规则

系统还实现 IG/TWIG（Bernoulli KL 信息增益及公开可达性权重）、PTR（消息对可搜索 survivor mass 的反事实变化）以及 Bits、AoI、TV（负载、信息年龄和公共 belief 总变差）等规则。这些规则及其确认、意图价值一起构成完整通信策略；匹配成本实验比较的是完整价值规则，不把所有差异单独归因于 EToM softmax。

### 2.4 成功调整、速率选择与 exact DP

若传输选项的语义价值为 $V_m$，链路成功概率为 $p_{m,r}$，给定符号价格 $\eta$，其净价值为
$$
u_{m,r}=V_mp_{m,r}-\eta n_{m,r}.
$$
对每个 EVID、CONF、INTENT 候选组，单个 agent 的逐时隙预算问题为
$$
\max \sum_g u_{g,o_g},\qquad \sum_g n_{g,o_g}\leq B,
$$
每组至多选择一个选项，也可以不发送。动态规划状态 $DP[b]$ 表示使用 $b$ 个符号时的最大净价值，按候选组选项更新。该“精确”仅指给定离散候选、估值和预算下的组合解，不意味着价值模型无误或全程任务全局最优。

### 2.5 共享上行、控制开销与接收融合

正交上行给每个 agent 独立的每时隙符号预算。共享上行支持 static（平均预留）、price（按需求更新影子价格）和 central（集中合并求解）三种模式。周期/FIFO 基线使用 max-min water filling。静态模式中未使用额度不能被其他 agent 借用，因此它适合测量固定共享约束下的行为，但不代表所有共享资源策略。

调度后，信道根据瞬时衰落决定是否解码；失败消息保留在队列或等待重传；成功消息由协调器融合并广播。上行 payload、包头、ACK、请求、授权和下行广播分别记账，表格中的总符号必须说明计入范围。协调器更新公共 belief、公开位置、公开意图、确认目标和救援任务，再向各 agent 发送可能丢失或延迟的公共快照。

### 2.6 EToM 计算优化与复杂度

估值在一个快照内共享公共几何因子、基准效用和公开意图结果；缓存不跨时隙，也不读取队友私有信息。前后缀分解避免为每个接收者重复构造队友排斥乘积。令 $A$ 为 agent 数、$G$ 为动作网格数、$C$ 为证据候选数，主要几何项由
$$
O(A^2G)\rightarrow O(AG)
$$
降低，含候选估值的主项由
$$
O((A^2+AC)G)\rightarrow O((A+AC)G)
$$
降低。缓存以额外内存交换重复计算，因此同时报告峰值分配和行为审计。

## 3 仿真设置与结果分析

### 3.1 实验矩阵和统计方法

实验分为三个证据组：纯 Planner 的价值规则匹配成本实验；32×32 网格、多团队规模的 EToM 计算实验；以及三 Planner 加 Qwen3、Llama 3.1、Gemma 3 的混合团队 campaign。匹配成本实验使用六种价值规则、13 个价格、20 个调价种子和 50 个测试种子，目标为 5,000、10,000、20,000 个上下行总符号。价格端点和混合概率在测试前冻结。计算计时包括模型构建、意图和证据候选估值，不包括共同证据聚合、信道和调度。混合 campaign 共 1,380 个任务。

区间使用报告定义的配对 percentile bootstrap，10,000 次重采样，按任务 seed 成簇；多组比较未作多重比较校正。因此结论是当前场景下的探索性证据。

### 3.2 价值规则的匹配成本结果

**表 1  纯 Planner 团队的成本标准化平均完成时隙**

| 总符号预算 | EToM | Bits | AoI | PTR | IG | TWIG |
|---:|---:|---:|---:|---:|---:|---:|
| 5,000 | 82.3 | 86.6 | 154.6 | 101.8 | 92.0 | 98.4 |
| 10,000 | 71.6 | 75.1 | 110.6 | 98.6 | 82.1 | 87.5 |
| 20,000 | 67.4 | 71.8 | 71.1 | 70.0 | 73.4 | 69.9 |

差值定义为“基线完成时隙减 EToM 完成时隙”，正值表示 EToM 更快。5,000 符号点的差值为 Bits 4.2 [-6.7, 15.1]、AoI 72.2 [55.0, 90.1]、PTR 19.5 [8.3, 31.0]、IG 9.7 [-0.3, 19.2]、TWIG 16.1 [6.8, 26.0]。10,000 符号点为 Bits 3.4（区间不可稳定估计）、AoI 38.9 [23.4, 53.9]、PTR 27.0 [16.0, 38.2]、IG 10.5 [0.2, 21.3]、TWIG 15.8 [5.4, 26.3]。20,000 符号点为 Bits 4.4 [-3.1, 11.8]、AoI 3.6 [-3.2, 10.8]、PTR 2.5 [-4.0, 9.1]、IG 6.0 [-1.5, 14.3]、TWIG 2.4 [-5.0, 10.6]。

结果支持有边界的结论：低、中通信成本点的 EToM 完整价值规则相对若干基线有较短完成时隙；20,000 符号点没有明确优势，不能宣称其在所有预算或任务中全面优于其他规则。该实验是纯 Planner 团队，不能与混合 LLM campaign 合并解释。

![不同价值模型的任务与通信权衡](figures/paper/png/06_value_tradeoff.png)

**图 1  不同价值规则的成本与任务权衡。** 该图对应纯 Planner 匹配成本实验。

### 3.3 EToM 计算效率与行为保持

**表 2  32×32 网格、8 个证据前缀的估值耗时**

| Agent 数 | 历史 ToM ms | 缓存版 ms | 分解版 ms | 历史/分解加速比 |
|---:|---:|---:|---:|---:|
| 2 | 1.811 | 1.728 | 1.842 | 1.00 [0.98, 1.02] |
| 4 | 2.811 | 2.363 | 2.467 | 1.15 [1.12, 1.19] |
| 6 | 3.977 | 3.039 | 3.073 | 1.31 [1.27, 1.33] |
| 10 | 7.118 | 4.457 | 4.379 | 1.64 [1.61, 1.65] |
| 14 | 11.310 | 6.074 | 5.840 | 1.95 [1.93, 1.98] |
| 32 | 39.623 | 12.859 | 11.288 | 3.51 [3.45, 3.57] |
| 64 | 135.208 | 28.042 | 20.963 | 6.45 [6.36, 6.49] |

默认 6-agent 负载中，历史、缓存和分解实现分别为 3.977、3.039 和 3.073 ms；新增分解相对已有缓存的收益约为 1.00 [0.95, 1.01]。因此小团队的主要收益来自缓存和基准效用复用；14 个 agent 以上才出现更清晰的分解收益。64-agent 结果是计算压力测试，不是完整任务性能验证。最大绝对估值误差约为 1.14×10^-16，候选排序一致；80 对完整任务中调度、速率、解码包和任务输出均一致。该证据支持当前实现的计算改写保持离散行为，不支持任务时隙因此改善或硬件能耗因此降低。

![估值实现的计算扩展性](figures/paper/png/08_team_size.png)

**图 2  团队规模与估值耗时。** 规模压力测试只反映估值计算。

### 3.4 混合团队 Table XII 扩展

Table XII 扩展采用正交上行，每个 agent 每时隙 100 symbols。团队为 3 个 Planner、Qwen3 8B、Llama 3.1 8B 和 Gemma 3 12B。它扩展了团队结构，但不是原论文模型标签和数值的严格复现。

**表 3  三 Planner 加三种不同 LLM 的正交上行结果**

| 方法 | 平均完成时隙 | 平均上行符号 | 完成率 |
|---|---:|---:|---:|
| Genie | 74.00 | 0 | 100% |
| MICA | 83.08 | 12,924.25 | 100% |
| SEM | 91.75 | 47,989.75 | 100% |

Periodic-MICA 完成时间差为 8.67 个时隙，95% CI 为 [-20.00, 38.34]；Periodic/MICA 上行符号比为 3.71，95% CI 为 [2.65, 5.05]。当前样本支持 MICA 减少上行符号，但任务时长优势的区间包含 0，不能表述为确定的任务加速。

### 3.5 共享预算、SNR、FBL、下行和 rescue 敏感性

在进入信道敏感性分析前，先用同一混合团队和同一静态共享设置做价值模块消融。该消融不改变 Planner、LLM、消息协议或信道，只替换价值规则或关闭语义过滤。

**表 4  混合团队价值与过滤消融（300 symbols/slot，static）**

| 方案 | 平均完成时隙 | 平均上行符号 | 平均总符号 | 完成率 |
|---|---:|---:|---:|---:|
| MICA（EToM） | 108.50 | 8,685.83 | 12,217.17 | 100% |
| MICA-AoI | 91.75 | 20,116.92 | 25,914.25 | 100% |
| MICA-Bits | 89.00 | 19,374.00 | 25,291.33 | 100% |
| MICA-no-filter | 109.42 | 8,345.75 | 11,960.08 | 100% |

该结果直接表明价值规则会改变团队行为和通信轨迹：AoI、Bits 与 EToM 产生不同的完成时隙和符号用量，关闭语义过滤也会改变任务时长。它不支持 EToM 在该静态共享设置下全面优于 AoI 或 Bits；EToM 的优势更准确地表述为在较低上行符号消耗下维持完整任务完成，而行为价值是否转化为更短任务时间取决于共享资源和信道条件。因而 H1 应理解为“价值估计改变了消息优先级和团队行为”，而不是预先假设某个价值函数在所有指标上支配其他规则。

默认共享上行设置为 300 symbols/slot，shared_mode=static，六个 agent 各获得固定 50 symbols/slot，未使用额度不能被其他 agent 借用。

**表 5  共享 300 symbols/slot 的混合团队结果**

| 方法 | 平均完成时隙 | 平均上行符号 | 完成率 |
|---|---:|---:|---:|
| Genie | 74.00 | 不适用 | 100% |
| MICA | 108.50 | 8,685.83 | 100% |
| SEM | 90.50 | 24,267.17 | 100% |

Periodic/MICA 上行符号比为 2.79，95% CI 为 [2.11, 3.63]；Periodic-MICA 完成时间差为 -18.00 个时隙，95% CI 为 [-56.17, 18.25]。静态共享预算下 MICA 节省了符号，但样本平均完成时间高于 SEM，不能宣称 MICA 全面优于 SEM。

SNR 降低时，MICA 和 SEM 都需要更多重传；下行丢失或延迟会使公共 belief 不同步；有限码长会改变速率与成功概率的折衷；rescue 任务中 INTENT 的认领消息减少重复服务风险。结合表 4 的消融和表 5 的共享预算结果，H2 的可支持表述是“联合调度可降低通信符号，但任务时间优势依赖资源模式和信道条件”。这些图表只展示当前 12 个任务种子下的系统敏感性，不能替代更大规模的模型能力比较。

![任务进展](figures/paper/png/07_task_progress.png)

![共享预算结果](figures/paper/png/13_shared_budget.png)

![SNR 敏感性](figures/paper/png/10_snr.png)

![下行损伤](figures/paper/png/11_downlink_loss.png)

**图 3  共享资源、信道和下行条件下的任务与通信结果。** 具体团队、预算和成本口径以 reports/current_mixed/README.md 为准。

### 3.6 可复现性与局限性

完整 mixed campaign 的 manifest、metrics、records、summary 和图表位于 reports/current_mixed/；EToM 匹配成本位于 reports/etom/matched/；计算基准位于 reports/etom/factorized/ 和 reports/etom/optimized/。报告保存代码指纹、模型标签、Ollama 模型身份、任务种子和推理计数。项目测试覆盖仿真器、通信、EToM、LLM、调度和结果导出。

当前证据有四项限制：混合 campaign 每个配置使用 12 个任务种子，适合系统集成检查，不足以支持模型异质性的因果结论；EToM 使用 Boltzmann 行为假设，接收者模型尚未用真实人类或机器人轨迹校准；计算加速是在本机和 Python 分配追踪下测得，不能直接外推到硬件能耗；价值规则比较未作多重比较校正，成本标准化区间条件于冻结端点和混合概率。

## 4 结论

本文围绕一个核心问题展开：在部分可观测、异构智能体和有限无线资源同时存在时，如何判断什么信息值得传输，并以尽可能低的通信代价改变团队行为。系统将环境信念、Planner/LLM 决策、EVID/CONF/INTENT 消息、接收者价值估计、无线调度和统计评估连接成五层闭环。

第一项核心方法是 EToM 行为价值估计。它使用发送者可见的公共 belief、公开意图和几何状态，反事实预测消息是否会改变队友的目标、空间分工或救援认领，而不是只计算 bits 或 belief 差异。纯 Planner 匹配成本实验表明，EToM 在 5,000 和 10,000 总符号点相对部分规则有较好的标准化完成时隙，但 20,000 符号点没有明确优势。混合团队消融进一步显示，EToM、AoI、Bits 和关闭语义过滤会产生不同的任务时间和通信轨迹；这证明价值估计会改变团队行为，但不支持 EToM 在所有指标上支配其他规则。

第二项核心方法是 VoI-aware exact scheduler。它把语义价值、packet success probability、传输速率、包开销和共享符号价格放入同一个逐时隙多组选择问题。Table XII 混合团队扩展中，正交上行下 MICA 比 SEM 少用约 3.71 倍上行符号；默认静态共享上行下比值为 2.79，但 MICA 平均任务时间高于 SEM。因此联合调度的稳健结论是通信符号降低，任务时延仍依赖共享资源模式和信道条件。

第三项核心方法是统一协议下的可复现混合团队架构。三 Planner 与 Qwen3、Llama 3.1、Gemma 3 通过同一消息、信道和融合接口运行，完整 campaign 验证 1,380/1,380 个任务且无 LLM fallback。JSON schema、模型 digest、响应缓存、源代码指纹、matched seeds 和逐 agent 记录使模型行为差异可以被独立审计，而不会被通信机制混淆。

EToM 的缓存和前后缀分解降低了重复估值计算，并在数值、排序、离散调度和完整任务输出上保持一致。该结果支持当前实现的计算可审计性，不等同于任务时隙改善或硬件能耗降低。后续工作需要增加独立任务种子，使用真实接收者轨迹校准行为模型，比较动态共享资源协调，并在真实无线硬件上测量端到端时延和能耗。

本文结论限定于已报告的仿真环境、模型版本、预算、信道和统计协议。

## 参考文献

1. D. Gündüz et al., “Beyond transmitting bits: Context, semantics, and task-oriented communications,” *IEEE Journal on Selected Areas in Communications*, vol. 41, no. 1, pp. 5--41, 2023.
2. J. Shao, Y. Mao, and J. Zhang, “Learning task-oriented communication for edge inference: An information bottleneck approach,” *IEEE Journal on Selected Areas in Communications*, vol. 40, no. 1, pp. 197--211, 2022.
3. H. Xie, Z. Qin, X. Tao, and K. B. Letaief, “Task-oriented multi-user semantic communications,” *IEEE Journal on Selected Areas in Communications*, vol. 40, no. 9, pp. 2584--2597, 2022.
4. J. Holm et al., “Goal-oriented scheduling in sensor networks with application timing awareness,” *IEEE Transactions on Communications*, vol. 71, no. 8, pp. 4513--4527, 2023.
5. J. Foerster et al., “Learning to communicate with deep multi-agent reinforcement learning,” in *Advances in Neural Information Processing Systems*, vol. 29, 2016.
6. S. Sukhbaatar, A. Szlam, and R. Fergus, “Learning multiagent communication with backpropagation,” in *Advances in Neural Information Processing Systems*, vol. 29, 2016.
7. A. Das et al., “TarMAC: Targeted multi-agent communication,” in *Proceedings of ICML*, pp. 1538--1546, 2019.
8. J. Jiang and Z. Lu, “Learning attentional communication for multi-agent cooperation,” in *Advances in Neural Information Processing Systems*, vol. 31, 2018.
9. Y.-C. Liu et al., “When2com: Multi-agent perception via communication graph grouping,” in *Proceedings of CVPR*, pp. 4105--4114, 2020.
10. Y. Wang et al., “ToM2C: Target-oriented multi-agent communication and cooperation with theory of mind,” in *Proceedings of ICLR*, 2022.
11. S. Kaul, R. Yates, and M. Gruteser, “Real-time status: How often should one update?” in *Proceedings of IEEE INFOCOM*, pp. 2731--2735, 2012.
12. I. Kadota et al., “Scheduling policies for minimizing age of information in broadcast wireless networks,” *IEEE/ACM Transactions on Networking*, vol. 26, no. 6, pp. 2637--2650, 2018.
13. Y. Polyanskiy, H. V. Poor, and S. Verdú, “Channel coding rate in the finite blocklength regime,” *IEEE Transactions on Information Theory*, vol. 56, no. 5, pp. 2307--2359, 2010.
