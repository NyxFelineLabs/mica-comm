"""Check dataset import provenance, explicit aliases, and overwrite protection."""

import hashlib
import json

import pytest

from scripts.import_plot_results import BASELINE, REALISTIC, import_results, translate


def make_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    record = {"rows": [{"scheme": "legacy", "seed": 0, "symbols": 1234, "score": 0.125}]}
    for name in (*BASELINE, *REALISTIC, "rev_frontier"):
        (source / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")
    for name in ("noise", "overhead", "shared"):
        (source / f"{name}.jsonl").write_text(
            json.dumps(record["rows"][0]) + "\n\n" + json.dumps(record["rows"][0]) + "\n",
            encoding="utf-8",
        )
    return source


def test_import_preserves_observations_and_records_provenance(tmp_path):
    source = make_source(tmp_path)
    output = tmp_path / "imported"
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    import_results(source, output, {"legacy": "current"})
    assert json.loads((output / "robustness_frontier.json").read_text()) == {
        "rows": [{"scheme": "current", "seed": 0, "symbols": 1234, "score": 0.125}]
    }
    lines = (output / "noise.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["symbols"] == 1234 for line in lines)
    manifest = json.loads((output / "provenance.json").read_text())
    assert manifest["fresh_inference"] is False
    assert manifest["method_aliases"] == {"legacy": "current"}
    for item in manifest["files"]:
        assert item["source_sha256"] == hashlib.sha256(before[item["source_name"]]).hexdigest()
        assert (
            item["imported_sha256"]
            == hashlib.sha256((output / item["imported_name"]).read_bytes()).hexdigest()
        )
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before


def test_import_preflights_overwrites_before_writing(tmp_path):
    source = make_source(tmp_path)
    output = tmp_path / "imported"
    output.mkdir()
    existing = output / "shared.jsonl"
    existing.write_text("keep me", encoding="utf-8")
    with pytest.raises(FileExistsError):
        import_results(source, output)
    assert list(output.iterdir()) == [existing]
    assert existing.read_text() == "keep me"


def test_translation_preserves_unrelated_tokens_and_rejects_key_merges():
    aliases = {"legacy": "current"}
    assert translate({"legacy_bits": [1, 2.5, "notlegacy", "legacy-mode"]}, aliases) == {
        "current_bits": [1, 2.5, "notlegacy", "current-mode"]
    }
    with pytest.raises(ValueError, match="merge"):
        translate({"legacy": 1, "current": 2}, aliases)


def test_missing_source_does_not_create_output(tmp_path):
    source = make_source(tmp_path)
    (source / "snr.json").unlink()
    output = tmp_path / "imported"
    with pytest.raises(FileNotFoundError, match="snr.json"):
        import_results(source, output)
    assert not output.exists()


def test_import_preserves_method_names_by_default(tmp_path):
    source = make_source(tmp_path)
    output = tmp_path / "imported"
    import_results(source, output)
    imported = json.loads((output / "agents.json").read_text())
    assert imported["rows"][0]["scheme"] == "legacy"
    assert json.loads((output / "provenance.json").read_text())["method_aliases"] == {}


def test_aliases_apply_once_and_treat_replacement_text_literally():
    assert translate("first second", {"first": "second", "second": "third"}) == "second third"
    assert translate("first", {"first": r"method\1"}) == r"method\1"
