//! Public plan limits for `GET /pricing` and usage entitlements.
//!
//! API plan ids (`free`, `pro`, `enterprise`) align with marketing tiers on govbase.dev.
//! Hosted Stripe checkout for self-serve Pro uses `GOVAI_STRIPE_PRICE_PRO` (see `stripe_billing`).

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlanLimits {
    pub name: &'static str,
    pub evidence_events_per_month: u64,
    pub runs_per_month: u64,
    pub events_per_run: u64,
}

/// Authoritative Pro list price (EUR/month) for public docs and `GET /pricing` metadata.
pub const PRO_LIST_PRICE_EUR_MONTHLY: u32 = 499;

pub fn get_plans() -> Vec<PlanLimits> {
    vec![
        PlanLimits {
            name: "free",
            evidence_events_per_month: 2_500,
            runs_per_month: 25,
            events_per_run: 1_000,
        },
        PlanLimits {
            name: "pro",
            evidence_events_per_month: 250_000,
            runs_per_month: 2_500,
            events_per_run: 10_000,
        },
        PlanLimits {
            name: "enterprise",
            evidence_events_per_month: 1_000_000,
            runs_per_month: 10_000,
            events_per_run: 20_000,
        },
    ]
}

/// Legacy alias: older docs/tests referred to the third API tier as `team`.
pub fn legacy_team_plan_alias() -> &'static str {
    "enterprise"
}

pub fn plan_limits_by_name(name: &str) -> Option<PlanLimits> {
    let lowered = name.trim().to_ascii_lowercase();
    let normalized = match lowered.as_str() {
        "team" => legacy_team_plan_alias(),
        other => other,
    };
    get_plans()
        .into_iter()
        .find(|p| p.name == normalized)
}

/// Default when no Stripe subscription is linked (sync fallback).
pub fn resolve_plan(_api_key: &str) -> &'static str {
    "free"
}

pub fn commercial_tier_display_name(plan_id: &str) -> &'static str {
    match plan_id {
        "pro" => "Pro",
        "enterprise" => "Enterprise",
        "strategic" => "Strategic Programs",
        _ => "Free",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_team_alias_maps_to_enterprise_limits() {
        let ent = plan_limits_by_name("enterprise").expect("enterprise");
        let team = plan_limits_by_name("team").expect("team alias");
        assert_eq!(ent.evidence_events_per_month, team.evidence_events_per_month);
    }

    #[test]
    fn pro_list_price_is_authoritative() {
        assert_eq!(PRO_LIST_PRICE_EUR_MONTHLY, 499);
    }
}
