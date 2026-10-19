"""Replay our measured LLM missions offline and verify every mission metric."""

import argparse
import json
from pathlib import Path

from mica_comm import Config, llm_agent, run_episode
from mica_comm.agents.llm_agent import LLMClient
from mica_comm.core.provenance import source_fingerprint


def offline(_body):
    """Reject cache misses so a replay cannot silently become a new inference run."""
    raise RuntimeError("Offline replay requires an existing response for every prompt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    checked = []
    fields = (
        "completion_time",
        "completed",
        "found",
        "bits",
        "symbols",
        "delivered_bits",
        "dl_symbols",
        "false_declarations",
        "confirm_latency",
        "llm_decisions",
        "llm_fallbacks",
    )
    args.output.mkdir(parents=True)
    for manifest_path in sorted(args.input.glob("*/manifest.json")):
        old = json.loads(manifest_path.read_text())
        model = old["model"]
        client = LLMClient(model, str(manifest_path.parent / "cache"), transport=offline)

        # Fail immediately on a cache miss without invoking retry/fallback behavior.
        def choose(prompt, labels, _choose=client.choose, _client=client):
            import hashlib

            key = hashlib.sha256(
                f"{_client.model}\n{prompt}\n{','.join(labels)}".encode()
            ).hexdigest()
            if key not in _client.cache:
                raise RuntimeError(f"Missing cached decision for {model}: {key}")
            return _choose(prompt, labels)

        client.choose = choose
        llm_agent._CLIENTS[model] = client
        rows = [
            json.loads(line)
            for line in (manifest_path.parent / "missions.jsonl").read_text().splitlines()
        ]
        destination = args.output / manifest_path.parent.name
        destination.mkdir()
        with (destination / "missions.jsonl").open("w", encoding="utf-8") as stream:
            for row in rows:
                cfg = Config(**old["config"])
                if row["scenario"] != "default":
                    raise ValueError("This replay currently requires the default scenario")
                result = run_episode(cfg, row["scheme"], row["seed"])
                for field in fields:
                    if result[field] != row[field]:
                        raise AssertionError(
                            f"Changed {model}/{row['scheme']}/{row['seed']}: {field}"
                        )
                result.pop("curve")
                result.update(
                    model=model, scenario=row["scenario"], scheme=row["scheme"], seed=row["seed"]
                )
                stream.write(json.dumps(result) + "\n")
        updated = {
            **old,
            "source_sha256": source_fingerprint()["source_sha256"],
            "execution": "offline-cache-replay",
            "original_source_sha256": old["source_sha256"],
        }
        (destination / "manifest.json").write_text(json.dumps(updated, indent=2) + "\n")
        checked.append(
            {"model": model, "missions": len(rows), "cache_hits": client.hits, "http_requests": 0}
        )
        print(f"Verified {model}: {len(rows)} missions, no inference calls", flush=True)
    if len(checked) != 3:
        raise ValueError("Expected all three measured model campaigns")
    (args.output / "replay.json").write_text(
        json.dumps({"verified": checked, **source_fingerprint()}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
