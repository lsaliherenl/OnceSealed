"""D1: answer the checklist with Turnike-JEV-4B (the teammate's decision model) on the same excerpts as Jev and the LLM.

Runs in its own Linux environment (torch + transformers 5.x), not the project venv. Native Windows builds of
PyTorch lack the row-wise FP8 matmul kernel, so on Windows use WSL2 (tested: RTX 4060 Laptop, sm_89):

    uv venv ~/turnike-venv --python 3.12
    uv pip install --python ~/turnike-venv/bin/python torch --index-url https://download.pytorch.org/whl/cu128
    uv pip install --python ~/turnike-venv/bin/python "transformers>=5.17,<6" "peft>=0.21" safetensors accelerate torchao
    HF_HOME=/mnt/c/Users/<you>/.cache/huggingface ~/turnike-venv/bin/python scripts/run_turnike.py --fp8
                                            # FP8 weights, ~4.5 GB GPU (sm_89+); HF_HOME reuses a Windows download
    python scripts/run_turnike.py --bf16    # merged bf16 weights, ~9 GB GPU (e.g. Colab)

Reads data/eval/reranker_inputs.jsonl (scripts/export_reranker_inputs.py) and writes
data/eval/answers_turnike_fp8.json or answers_turnike_bf16.json in the shape scripts/eval_metrics.py expects.
Each question gets the same wording Jev 1.13 got. karar.py (the model's inference module, Apache-2.0) is
downloaded from the model repository at a recorded revision.
"""

import argparse
import importlib.util
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "eval"
REPO = "berkay123001/turnike-jev-4b"
WEIGHTS = {"fp8": "berkay123001/turnike-jev-4b-fp8", "bf16": "berkay123001/turnike-jev-4b-merged"}
JEV_SUFFIX = " Judge only the text provided; answer about this excerpt."  # as in run_checklist_models.ask_jev


def load_karar(revision: str | None):
    from huggingface_hub import HfApi, hf_hub_download

    rev = revision or HfApi().model_info(REPO).sha
    path = hf_hub_download(REPO, "karar.py", revision=rev)
    spec = importlib.util.spec_from_file_location("karar", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, rev


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fp8", action="store_true")
    mode.add_argument("--bf16", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--revision", help="karar.py revision of the model repo (default: latest)")
    parser.add_argument("--out-dir", default=str(EVAL))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    import torch
    from huggingface_hub import HfApi

    variant = "fp8" if args.fp8 else "bf16"
    karar, karar_rev = load_karar(args.revision)
    weights_rev = HfApi().model_info(WEIGHTS[variant]).sha
    t0 = time.perf_counter()
    model = karar.Karar(None, taban=WEIGHTS[variant])  # merged weights; the FP8 repo is already quantized
    load_s = time.perf_counter() - t0

    items: dict[str, dict] = defaultdict(lambda: {"questions": {}})
    for line in (EVAL / "reranker_inputs.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        item_id, qid = row["key"].split("|")
        items[item_id]["document"] = row["document"]
        items[item_id]["questions"][qid] = {"type": "noul", "instructions": row["query"] + JEV_SUFFIX}

    runs = []
    for r in range(args.runs):
        answers = {}
        for item_id, item in items.items():
            t = time.perf_counter()
            out = model.sor(item["document"], item["questions"])  # one forward pass for all questions of the item
            ms = round((time.perf_counter() - t) * 1000)
            for qid, dist in out.items():
                answers[f"{item_id}|{qid}"] = {"p_yes": dist["true"], "model": WEIGHTS[variant],
                                               "latency_ms": ms, "cost": 0}
        runs.append(answers)
        print(f"  run {r + 1}/{args.runs}: {len(answers)} answers, {model.kesilen} truncated prompts so far")

    out = {"question_set_version": "qs-v2-checklist", "model": f"turnike_{variant}",
           "label": f"Turnike-JEV-4B ({variant.upper()})", "weights": WEIGHTS[variant], "weights_revision": weights_rev,
           "karar_py_revision": karar_rev, "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
           "load_seconds": round(load_s, 1), "runs": runs}
    path = Path(args.out_dir) / f"answers_turnike_{variant}.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
