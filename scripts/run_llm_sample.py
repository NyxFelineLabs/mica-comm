"""Re-simulate one mixed-team mission with a separate response cache."""

import argparse
import json

from mosaic_comm import Config, llm_agent, run_episode
from mosaic_comm.paths import RESULTS_DIR

RUNS = RESULTS_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small_reasoner")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--seeds", type=int, default=1, help="number of consecutive seeds starting at --seed"
    )
    ap.add_argument("--schemes", nargs="+", default=["sem", "mica"])
    ap.add_argument(
        "--planner", action="store_true", help="run the planner-only reference with the same seeds"
    )
    args = ap.parse_args()

    cache_dir = RUNS / "llm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = llm_agent.LLMClient(args.model, cache_dir=str(cache_dir))
    llm_agent._CLIENTS[args.model] = client

    for seed in range(args.seed, args.seed + args.seeds):
        name = "planner" if args.planner else args.model.replace(":", "_")
        output = RUNS / f"llm_sample_{name}_seed{seed}.jsonl"
        done = set()
        if output.exists():
            with output.open() as f:
                done = {json.loads(line)["scheme"] for line in f if line.strip()}
        for scheme in args.schemes:
            if scheme in done:
                continue
            before_hits, before_calls = client.hits, client.calls
            cfg = Config().with_(llm_agents=() if args.planner else (0, 2, 4), llm_model=args.model)
            result = run_episode(cfg, scheme, seed)
            result.pop("curve", None)
            result.update(
                scheme=scheme,
                seed=seed,
                model=None if args.planner else args.model,
                cache_hits=client.hits - before_hits,
                online_calls=client.calls - before_calls,
            )
            if result.get("llm_fallbacks", 0):
                raise SystemExit(
                    f"seed {seed} {scheme}: LLM request failed; "
                    "result is not a valid mixed-team run"
                )
            with output.open("a") as f:
                f.write(json.dumps(result) + "\n")
            print(
                f"seed {seed} {scheme}: T={result['completion_time']} "
                f"uses={result['symbols']} hits={result['cache_hits']} "
                f"calls={result['online_calls']} fallbacks=0",
                flush=True,
            )


if __name__ == "__main__":
    main()
