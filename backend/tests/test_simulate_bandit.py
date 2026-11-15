from ml import simulate_bandit as sim


def test_bandit_simulation_is_labeled_and_adaptive_learns(tmp_path, monkeypatch):
    monkeypatch.setattr(sim, "ARTIFACT", tmp_path / "bandit_sim.json")
    monkeypatch.setattr(sim, "REPEATS", 3)
    out = sim.main()
    assert "SIMULATION" in out["label"]
    assert (tmp_path / "bandit_sim.json").exists()
    first5, last5 = out["headline"]["adaptive_first5_vs_last5"]
    assert last5 > first5                                    # it learns over time
    pol = out["policies"]
    assert pol["adaptive"]["ends_on_best_style"]["mean"] > pol["fixed"]["ends_on_best_style"]["mean"]
    assert pol["adaptive"]["teachback_success_rate"]["mean"] > pol["random"]["teachback_success_rate"]["mean"]
