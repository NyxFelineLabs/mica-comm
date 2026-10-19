"""Display-only Chinese localization; experiment values and IDs stay untouched."""

import os
import re
from pathlib import Path

from matplotlib import font_manager


def chinese():
    return os.environ.get("MICA_FIGURE_LANGUAGE", "en") == "zh"


def fonts():
    if not chinese():
        return ["Arial", "DejaVu Sans", "Liberation Sans"]
    # Reuse Windows fonts from WSL. Do not bundle proprietary font files in Git.
    for file in (Path("C:/Windows/Fonts/msyh.ttc"), Path("/mnt/c/Windows/Fonts/msyh.ttc")):
        if file.exists():
            font_manager.fontManager.addfont(str(file))
            return ["Microsoft YaHei"]
    for name in ("Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Zen Hei"):
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return [name]
        except ValueError:
            pass
    raise RuntimeError("Chinese plots require SimHei, Noto Sans SC or WenQuanYi Zen Hei")


TRANSLATIONS = {
    "Completion time (slots)": "任务完成时间（时隙）",
    "Number of agents, $K$": "智能体数量 $K$",
    "Channel uses per agent per slot, $W$": "每智能体每时隙信道使用次数 $W$",
    "Time slot": "时隙",
    "Survivors located (of 8)": "已定位幸存者数量（共 8 人）",
    "Report only": "仅上报确认",
    "Raw sensor data": "原始传感数据",
    "Natural language": "自然语言",
    "Semantic, periodic": "周期语义上报",
    "Ideal communication": "理想通信",
    "Ideal reference": "理想参考",
    "MICA w/o VoI": "MICA（无信息价值）",
    "Belief-divergence VoI": "信念差异信息价值",
    "MICA (ToM value)": "MICA（心智模型价值）",
    "Throughput value": "吞吐量价值",
    "Throughput value (bits)": "吞吐量价值（比特）",
    "Age-of-information value": "信息年龄价值",
    "Belief-divergence value": "信念差异价值",
    "Periodic aggregated ($k$ swept)": "周期聚合（扫描 $k$）",
    "Semantic periodic (default)": "周期语义上报（默认）",
    "Periodic, rate-aware": "周期上报＋速率感知",
    "Periodic, rate-aware + filter": "周期上报＋速率感知＋过滤",
    "Periodic, suppressing envelope": "周期抑制上报包络",
    "MICA (price swept)": "MICA（扫描价格）",
    "Periodic family, envelope": "周期策略族包络",
    "Semantic periodic, every slot": "逐时隙周期语义上报",
    "Channel uses per mission (×10³)": "每任务信道使用次数（千次）",
    "Channel uses (×10³)": "信道使用次数（千次）",
    "Uplink channel uses (×10³)": "上行信道使用次数（千次）",
    "Reference SNR at 100 m (dB)": "100 米参考信噪比（dB）",
    "Broadcast loss probability $p_\mathrm{DL}$": "广播丢失概率 $p_\mathrm{DL}$",
    "Broadcast delay $d_\mathrm{DL}$ (slots)": "广播延迟 $d_\mathrm{DL}$（时隙）",
    "Survivors saved (%)": "获救幸存者比例（%）",
    "Clustered survivors": "聚集分布的幸存者",
    "Value estimate (accuracy decreases to the right)": "价值估计方式（向右精度降低）",
    "Channel uses, periodic / MICA": "信道用量比：周期上报／MICA",
    "Search": "搜索任务",
    "Search, K=10": "搜索，K=10",
    "Search, clustered": "搜索，聚集分布",
    "Rescue": "救援任务",
    "Rescue, W=50": "救援，W=50",
    "Rescue, -5 dB": "救援，−5 dB",
    "exact": "精确",
    "Decade": "数量级",
    "perm.": "置换",
    "perm.,\nno filt.": "置换，\n无过滤",
    "Task performance": "任务表现",
    "Task progress": "任务进度",
    "Communication cost": "通信开销",
    "Uplink symbols (thousands)": "上行符号数（千）",
    "Paired completion-time difference (slots; first minus second)": "配对完成时隙差（前者减后者）",
    "Fixed-cycle sharing (SYNC)": "固定周期协同（SYNC）",
    "Instant, reliable sharing reference (IDEAL)": "即时无误差参考（IDEAL）",
    "Shared uplink budget (symbols/slot)": "共享上行预算（符号／时隙）",
    "None": "无通信",
    "Periodic": "周期上报",
    "Risk priority": "风险优先",
    "Ideal delivery": "理想投递",
    "MICA, static belief": "MICA（静态信念）",
    "MICA, uniform assets": "MICA（均匀资产权重）",
    "MICA, no action value": "MICA（无行动价值）",
    "MICA ($\\eta$ swept)": "MICA（扫描 $\\eta$）",
}


def translate(text):
    if not chinese() or not text:
        return text
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    # Parameter-bearing titles and captions retain mathematical symbols/values.
    text = re.sub(r"Shared budget (\$?B[^=]*=\s*\d+\$?)", r"共享预算 \1", text)
    text = re.sub(r"Search task (.*)", r"搜索任务 \1", text)
    text = text.replace("channel uses per slot", "每时隙信道使用次数")
    text = text.replace("agents", "个智能体").replace("Semantic, periodic:", "周期语义上报：")
    text = text.replace("slots", "时隙").replace("FBL, no coding gap", "有限码长，无编码间隙")
    text = text.replace("FBL, coding gap", "有限码长，编码间隙")
    text = text.replace("Target ", "目标 ").replace("minus ", "减去 ")
    text = text.replace("no filt.", "无过滤").replace("perm.", "置换").replace("exact", "精确")
    text = text.replace("Decade", "数量级")
    text = re.sub(r"Slot (\d+)", r"时隙 \1", text)
    text = text.replace("Column", "列坐标").replace("Row", "行坐标")
    return text


def localize_figure(fig):
    if not chinese():
        return
    from matplotlib.text import Text

    for artist in fig.findobj(match=Text):
        artist.set_text(translate(artist.get_text()))
