"""D49 integration tests with the real frozen and pooled models under D48.

Each parametrized environment runs a fresh interpreter with either the
portable-image sources (TW01_ variables) or the worktree sources (FMPA_).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE_DIR = Path(os.environ.get(
    "FMPA_V1EXT_IMAGE_DIR",
    ROOT / "outputs/quality_runs/tw01_docker_portable_final_20261015_025240_Windows5800X/TW01_Docker_Portable_v1.0.0",
))
TOKEN = "test_only_" + "m" * 48
pytestmark = pytest.mark.skipif(
    not (IMAGE_DIR / "catalog/catalog.json").is_file(),
    reason="portable immutable model source missing",
)


@pytest.fixture(scope="module", params=["portable_image", "worktree_repo"])
def output(request):
    repo = request.param == "worktree_repo"
    code = ROOT if repo else IMAGE_DIR
    prefix = "FMPA_" if repo else "TW01_"
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("FMPA_", "TW01_", "PROBE_"))}
    env.update({
        "PYTHONPATH": os.pathsep.join([
            str(code / "src"), str(code / "deploy/oracle-forecastengine"),
            str(HERE.parent / "v1_full_catalog"),
            str(HERE.parent / "rolling_history"), str(HERE),
        ]),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PROBE_TOKEN": TOKEN, "PROBE_SOURCE_PREFIX": prefix,
        prefix + "ORIGIN_API_TOKEN": TOKEN,
        # This detached worktree contains tracked source, not the immutable
        # model bytes; both environments use the same allowed portable release.
        prefix + "RELEASE_DIR": str(IMAGE_DIR / "models/releases/0.1.0"),
        prefix + "EXTENDED_CATALOG_DIR": str(IMAGE_DIR / "catalog"),
        prefix + "POOLED_ML_DIR": str(IMAGE_DIR / "models/pooled"),
    })
    done = subprocess.run(
        [sys.executable, str(HERE / "all_markets_probe.py")],
        cwd=str(HERE), env=env, capture_output=True, text=True,
        encoding="utf-8", timeout=900,
    )
    assert done.returncode == 0, done.stderr[-8000:]
    result = json.loads(done.stdout.strip().splitlines()[-1])
    for name, item in result["cases"].items():
        print(f"D49 {prefix} {name}: count={item['market_count']}, "
              f"timings={item['elapsed_seconds']}, avg={item['mean_seconds']}, max={item['max_seconds']}")
    return result


def test_all_markets_uses_rolling_history_and_both_original_model_families(output):
    assert output["rolling_cutoff"] == "2026-10-03"
    assert output["published"] == "switched"
    assert output["patched"] == ["all_markets_runtime", "all_markets_runtime"]
    assert output["cases"]["frozen"]["model"] != "multi-crop-ml/1.0.0"
    assert output["cases"]["pooled"]["model"] == "multi-crop-ml/1.0.0"
    assert output["snapshot_verifications_per_frozen_request"] == 1
    for item in output["cases"].values():
        assert item["market_count"] >= 3
        assert item["cutoff"] == "2026-10-03"


def test_all_markets_stays_within_original_15_second_timeout(output):
    for item in output["cases"].values():
        assert len(item["elapsed_seconds"]) == 3
        assert item["max_seconds"] < 15, item


def test_invalid_quote_and_less_than_three_markets_return_no_number(output):
    assert output["quote_all"] == {"status": 422, "code": "unsupported_market"}
    assert output["insufficient"] == {"status": 503, "code": "stale_data_unusable"}


def test_named_market_is_the_exact_original_path(output):
    assert output["named_market_parity"] == "all deterministic fields identical"


def test_real_oracle_aggregate_envelopes_pass_worker_and_tampering_does_not(output):
    """Use actual D48+model output across the Python/Node trust boundary."""
    worker = ROOT / "deploy/cloudflare-workers-mcp"
    script = """
      import { verifyOracleEnvelope } from './src/contracts.js';
      let text = '';
      for await (const chunk of process.stdin) text += chunk;
      const envelopes = JSON.parse(text);
      for (const envelope of envelopes) {
        const args = envelope.input_echo;
        if (verifyOracleEnvelope('post_forecast', args, envelope) !== envelope)
          throw Error('Worker changed a real Oracle result');
        const tampered = structuredClone(envelope);
        tampered.engine_result.results[0].relative_change_estimate += 0.01;
        try {
          verifyOracleEnvelope('post_forecast', args, tampered);
          throw Error('Worker accepted a corrupted real Oracle result');
        } catch (error) {
          if (error.message === 'Worker accepted a corrupted real Oracle result') throw error;
        }
      }
      process.stdout.write('2 real Oracle envelopes verified and both tampering attempts rejected');
    """
    bodies = [output["cases"][name]["envelope"]["body"] for name in ("frozen", "pooled")]
    done = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=str(worker), input=json.dumps(bodies, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("2 real Oracle envelopes verified")


def test_negative_control_mean_cannot_replace_median(output):
    assert output["negative_mean_control"] is True


def test_negative_control_replacing_median_with_mean_fails():
    """Deliberately swap the aggregation function; the real-output assertion MUST fail."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("FMPA_", "TW01_", "PROBE_"))}
    env.update({
        "PYTHONPATH": os.pathsep.join([
            str(IMAGE_DIR / "src"), str(IMAGE_DIR / "deploy/oracle-forecastengine"),
            str(HERE.parent / "v1_full_catalog"),
            str(HERE.parent / "rolling_history"), str(HERE),
        ]),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PROBE_TOKEN": TOKEN, "PROBE_SOURCE_PREFIX": "TW01_",
        "PROBE_FORCE_MEAN": "1",
        "TW01_ORIGIN_API_TOKEN": TOKEN,
        "TW01_RELEASE_DIR": str(IMAGE_DIR / "models/releases/0.1.0"),
        "TW01_EXTENDED_CATALOG_DIR": str(IMAGE_DIR / "catalog"),
        "TW01_POOLED_ML_DIR": str(IMAGE_DIR / "models/pooled"),
    })
    done = subprocess.run(
        [sys.executable, str(HERE / "all_markets_probe.py")],
        cwd=str(HERE), env=env, capture_output=True, text=True,
        encoding="utf-8", timeout=900,
    )
    assert done.returncode != 0
    assert "median mismatch" in done.stderr
