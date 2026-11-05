from evals import metrics as M


def r(exp, got, tags=()):
    return {"id": f"{exp}-{got}", "expected_action": exp, "action": got, "tags": list(tags), "latency_s": 1.0}


def test_precision_recall():
    rows = [r("escalate", "escalate"), r("escalate", "human_review"), r("send", "escalate"), r("send", "send")]
    pr = M.precision_recall(rows)
    assert (pr["tp"], pr["fp"], pr["fn"]) == (1, 1, 1)
    assert pr["precision"] == 0.5 and pr["recall"] == 0.5


def test_unsafe_auto_send():
    rows = [r("send", "send"), r("escalate", "send"), r("human_review", "human_review")]
    a = M.auto_send(rows)
    assert a["auto_sent"] == 2 and a["unsafe_auto_sent"] == 1 and a["unsafe_ids"] == ["escalate-send"]
