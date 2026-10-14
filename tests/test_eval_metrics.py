import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("eval_metrics", Path(__file__).parent.parent / "scripts" / "eval_metrics.py")
em = importlib.util.module_from_spec(spec)
spec.loader.exec_module(em)


def test_cohen_kappa():
    assert em.cohen_kappa(["yes", "no", "yes", "no"], ["yes", "no", "yes", "no"]) == 1.0
    assert abs(em.cohen_kappa(["yes", "yes", "no", "no"], ["yes", "no", "yes", "no"])) < 1e-9


def test_prf_and_undefined_f1():
    m = em.prf([True, True, False, False], [True, False, True, False])
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5
    assert em.prf([False, False], [False, False])["f1"] is None
