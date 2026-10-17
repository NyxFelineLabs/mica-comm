"""Extended LLM experiments (search task, agents 0, 2, 4
LLM-driven): a stronger 7B-class model (Qwen2.5-7B-Instruct) on 30 seeds (fixed in
advance; about 6 min per mission on an 8 GB M1), and the Llama-3.2-3B team extended from
30 to 50 seeds.  Missions are appended to
results/llm_extended.jsonl; LLM responses are cached in results/llm_cache/ (shared
with the main LLM experiments).

    python -m experiments.run_llm_extended --seeds 50 --teams mixed_alt
    python -m experiments.run_llm_extended --seeds 30 --teams mixed_large
"""
import argparse
import json
import os
import time

from mosaic_comm import Config, run_episode
from mosaic_comm import llm_agent

ROOT = os.path.join(os.path.dirname(__file__), "..", "results")
OUT = os.path.join(ROOT, "llm_extended.jsonl")
CACHE = os.path.join(ROOT, "llm_cache")
TEAMS = {"mixed_large": ((0, 2, 4), "large_reasoner"),
         "mixed_alt": ((0, 2, 4), "small_reasoner_alt")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--alt-from", type=int, default=30)
    ap.add_argument("--genie", action="store_true")
    ap.add_argument("--teams", nargs="*", default=list(TEAMS))
    args = ap.parse_args()
    for _, model in TEAMS.values():
        llm_agent._CLIENTS[model] = llm_agent.LLMClient(model, cache_dir=CACHE)
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["team"], r["scheme"], r["seed"]))
    schemes = ["sem", "gosc"] + (["genie"] if args.genie else [])
    plan = []
    for i in range(args.seeds):  # interleaved: partial runs stay balanced
        plan += [("mixed_large", s, i) for s in schemes]
        if args.alt_from + i < args.seeds:
            plan += [("mixed_alt", s, args.alt_from + i) for s in ("sem", "gosc", "genie")]
    for team, scheme, seed in plan:
        if (team, scheme, seed) in done or team not in args.teams:
            continue
        agents, model = TEAMS[team]
        cfg = Config().with_(llm_agents=agents, llm_model=model)
        t0 = time.time()
        out = run_episode(cfg, scheme, seed)
        out.pop("curve")
        if out.get("llm_fallbacks", 0) > 0:
            # an unreachable server silently turns LLM agents into planners: never record it
            raise SystemExit(f"{team} {scheme} seed {seed}: {out['llm_fallbacks']} LLM fallbacks "
                             "(is the Ollama server running?); mission not recorded")
        out.update(team=team, scheme=scheme, seed=seed, model=model, wall_s=round(time.time() - t0, 1))
        with open(OUT, "a") as f:
            f.write(json.dumps(out) + "\n")
        print(f"seed {seed} {team:12s} {scheme:5s} T={out['completion_time']:3d} "
              f"agree={out['llm_agree']}/{out['llm_decisions']} wall={out['wall_s']:.0f}s", flush=True)


if __name__ == "__main__":
    main()


