# Robustness evaluation

Robustness evaluation captures **input perturbation degradation**, **jailbreak attempt success rates**, and a **stability score** summarising regression behaviour in offline harnesses.

## Signals

| Field | Meaning |
| --- | --- |
| `input_perturbation_degradation_percent` | Measured quality drop under controlled perturbations |
| `jailbreak_attempt_success_rate_percent` | Success rate of jailbreak prompts in eval (target: zero for promotion) |
| `stability_score` | Normalised stability metric (0–100) |

## Tooling

Non-zero jailbreak success rates trigger **fail-closed** scoring (`ok: false`) when combined with other gates. See `scripts/model_risk_score.py` for exact thresholds.

## Related

- [Fairness evaluation](fairness-evaluation.md)
- [README](README.md)
