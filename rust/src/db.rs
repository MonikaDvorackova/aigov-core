use chrono::{DateTime, Utc};
use sqlx::Row;
use sqlx::{postgres::PgPoolOptions, PgPool};
use std::path::Path;
use uuid::Uuid;

pub type DbPool = PgPool;

/// Count of `.sql` files under `rust/migrations/`. Updated when migrations are added; tests assert parity.
pub const EXPECTED_SQLX_MIGRATION_COUNT: i64 = 2;

pub fn postgres_url_configured_nonempty() -> Result<(), String> {
    let url = std::env::var("GOVAI_DATABASE_URL")
        .or_else(|_| std::env::var("DATABASE_URL"))
        .unwrap_or_default();
    if url.trim().is_empty() {
        return Err(
            "Missing Postgres URL: set GOVAI_DATABASE_URL (preferred) or DATABASE_URL.".to_string(),
        );
    }
    Ok(())
}

/// Returns `Err` unless `_sqlx_migrations` reports at least [`EXPECTED_SQLX_MIGRATION_COUNT`] successful applies.
pub async fn verify_sqlx_migrations_complete(pool: &DbPool) -> Result<(), String> {
    let applied: i64 = sqlx::query_scalar(
        "select count(*)::bigint from _sqlx_migrations where success = true",
    )
    .fetch_one(pool)
    .await
    .map_err(|e| {
        let msg = e.to_string();
        if msg.contains("_sqlx_migrations")
            || msg.contains("does not exist")
            || msg.contains("relation")
        {
            "Postgres schema not migrated: `_sqlx_migrations` unavailable or migrations not applied."
                .to_string()
        } else {
            format!("could not verify migration state: {}", e)
        }
    })?;

    if applied < EXPECTED_SQLX_MIGRATION_COUNT {
        return Err(format!(
            "Postgres migrations incomplete: {} successful migrations recorded in `_sqlx_migrations`, expected {}. Apply repo migrations out-of-band or set GOVAI_AUTO_MIGRATE=true.",
            applied, EXPECTED_SQLX_MIGRATION_COUNT
        ));
    }
    Ok(())
}

/// Apply SQL migrations from `rust/migrations` using runtime discovery (PostgreSQL-only).
pub async fn run_sqlx_migrations(pool: &DbPool) -> Result<(), String> {
    let migrations_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("migrations");
    let migrator = sqlx_core::migrate::Migrator::new(migrations_dir)
        .await
        .map_err(|e| format!("migration source error: {e}"))?;
    migrator
        .run(pool)
        .await
        .map_err(|e| format!("migration failed: {e}"))
}

pub async fn init_pool_from_env() -> Result<DbPool, String> {
    postgres_url_configured_nonempty()?;
    let database_url = std::env::var("GOVAI_DATABASE_URL")
        .or_else(|_| std::env::var("DATABASE_URL"))
        .map_err(|_| {
            "Missing Postgres URL: set GOVAI_DATABASE_URL (preferred) or DATABASE_URL.".to_string()
        })?;
    PgPoolOptions::new()
        .max_connections(10)
        .connect(&database_url)
        .await
        .map_err(|e| format!("DB connect failed: {}", e))
}

pub struct UserTeamRow {
    pub team_id: Uuid,
    pub team_name: String,
    pub role: String,
}

pub async fn list_user_teams(
    pool: &DbPool,
    user_id: &Uuid,
) -> Result<Vec<UserTeamRow>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select tm.team_id as team_id,
               t.name as team_name,
               tm.role as role
        from public.team_members tm
        join public.teams t on t.id = tm.team_id
        where tm.user_id = $1
        order by tm.created_at asc
        "#,
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;

    Ok(rows
        .into_iter()
        .map(|r| UserTeamRow {
            team_id: r.get::<Uuid, _>("team_id"),
            team_name: r.get::<String, _>("team_name"),
            role: r.get::<String, _>("role"),
        })
        .collect())
}

pub async fn is_team_member(
    pool: &DbPool,
    team_id: Uuid,
    user_id: Uuid,
) -> Result<bool, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select 1
        from public.team_members
        where team_id = $1 and user_id = $2
        limit 1
        "#,
    )
    .bind(team_id)
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    Ok(row.is_some())
}

pub async fn get_team_member_role(
    pool: &DbPool,
    team_id: Uuid,
    user_id: Uuid,
) -> Result<Option<String>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select role
        from public.team_members
        where team_id = $1 and user_id = $2
        limit 1
        "#,
    )
    .bind(team_id)
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| r.get::<String, _>("role")))
}

pub async fn get_default_team_for_user(
    pool: &DbPool,
    user_id: Uuid,
) -> Result<Option<Uuid>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select team_id
        from public.team_members
        where user_id = $1
        order by created_at asc
        limit 1
        "#,
    )
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| r.get::<Uuid, _>("team_id")))
}

pub async fn bootstrap_team_for_user(pool: &DbPool, user_id: Uuid) -> Result<Uuid, sqlx::Error> {
    let team_id = Uuid::new_v4();
    let name = "Default team".to_string();

    let mut tx = pool.begin().await?;

    sqlx::query(
        r#"
        insert into public.teams (id, name)
        values ($1, $2)
        "#,
    )
    .bind(team_id)
    .bind(name)
    .execute(&mut *tx)
    .await?;

    sqlx::query(
        r#"
        insert into public.team_members (team_id, user_id, role)
        values ($1, $2, 'admin')
        "#,
    )
    .bind(team_id)
    .bind(user_id)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;
    Ok(team_id)
}

#[cfg(test)]
mod migration_count_tests {
    use super::EXPECTED_SQLX_MIGRATION_COUNT;

    #[test]
    fn expected_sqlx_migration_count_matches_migrations_directory() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("migrations");
        let n = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("read migrations dir {:?}: {}", dir, e))
            .filter_map(|e| e.ok())
            .filter(|e| e.path().extension().map_or(false, |x| x == "sql"))
            .count() as i64;
        assert_eq!(
            n, EXPECTED_SQLX_MIGRATION_COUNT,
            "update EXPECTED_SQLX_MIGRATION_COUNT when adding/removing migrations"
        );
    }
}

pub struct AssessmentRow {
    pub id: Uuid,
    pub team_id: Uuid,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub status: String,
    pub system_name: Option<String>,
    pub intended_purpose: Option<String>,
    pub risk_class: Option<String>,
}

pub async fn insert_assessment(
    pool: &DbPool,
    team_id: Uuid,
    created_by: Uuid,
    system_name: String,
    intended_purpose: String,
    risk_class: String,
) -> Result<AssessmentRow, sqlx::Error> {
    let id = Uuid::new_v4();

    let row = sqlx::query(
        r#"
        insert into public.assessments (
            id,
            team_id,
            created_by,
            status,
            system_name,
            intended_purpose,
            risk_class
        )
        values ($1, $2, $3, 'draft', $4, $5, $6)
        returning
            id,
            team_id,
            created_by,
            created_at,
            status,
            system_name,
            intended_purpose,
            risk_class
        "#,
    )
    .bind(id)
    .bind(team_id)
    .bind(created_by)
    .bind(system_name)
    .bind(intended_purpose)
    .bind(risk_class)
    .fetch_one(pool)
    .await?;

    Ok(AssessmentRow {
        id: row.get::<Uuid, _>("id"),
        team_id: row.get::<Uuid, _>("team_id"),
        created_by: row.get::<Uuid, _>("created_by"),
        created_at: row.get::<DateTime<Utc>, _>("created_at"),
        status: row.get::<String, _>("status"),
        system_name: row.get::<Option<String>, _>("system_name"),
        intended_purpose: row.get::<Option<String>, _>("intended_purpose"),
        risk_class: row.get::<Option<String>, _>("risk_class"),
    })
}

// --- compliance workflow (app layer; team queue / override — not a second ledger projection) ---

pub struct ComplianceWorkflowRow {
    pub id: Uuid,
    pub team_id: Uuid,
    pub run_id: String,
    pub state: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Uuid,
    pub updated_by: Option<Uuid>,
}

fn map_workflow_row(row: &sqlx::postgres::PgRow) -> ComplianceWorkflowRow {
    ComplianceWorkflowRow {
        id: row.get::<Uuid, _>("id"),
        team_id: row.get::<Uuid, _>("team_id"),
        run_id: row.get::<String, _>("run_id"),
        state: row.get::<String, _>("state"),
        created_at: row.get::<DateTime<Utc>, _>("created_at"),
        updated_at: row.get::<DateTime<Utc>, _>("updated_at"),
        created_by: row.get::<Uuid, _>("created_by"),
        updated_by: row.get::<Option<Uuid>, _>("updated_by"),
    }
}

pub async fn upsert_workflow_pending(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
    user_id: Uuid,
) -> Result<ComplianceWorkflowRow, sqlx::Error> {
    let row = sqlx::query(
        r#"
        insert into public.compliance_workflow (
            team_id, run_id, state, created_by, updated_by
        )
        values ($1, $2, 'pending_review', $3, $3)
        on conflict (team_id, run_id) do nothing
        returning
            id,
            team_id,
            run_id,
            state,
            created_at,
            updated_at,
            created_by,
            updated_by
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .bind(user_id)
    .fetch_optional(pool)
    .await?;

    if let Some(r) = row {
        return Ok(map_workflow_row(&r));
    }

    let existing = get_compliance_workflow(pool, team_id, run_id).await?;
    existing.ok_or_else(|| sqlx::Error::RowNotFound)
}

pub async fn list_compliance_workflow(
    pool: &DbPool,
    team_id: Uuid,
    state_filter: Option<&str>,
) -> Result<Vec<ComplianceWorkflowRow>, sqlx::Error> {
    let rows = if let Some(st) = state_filter {
        sqlx::query(
            r#"
            select
                id,
                team_id,
                run_id,
                state,
                created_at,
                updated_at,
                created_by,
                updated_by
            from public.compliance_workflow
            where team_id = $1 and state = $2
            order by updated_at desc
            "#,
        )
        .bind(team_id)
        .bind(st)
        .fetch_all(pool)
        .await?
    } else {
        sqlx::query(
            r#"
            select
                id,
                team_id,
                run_id,
                state,
                created_at,
                updated_at,
                created_by,
                updated_by
            from public.compliance_workflow
            where team_id = $1
            order by updated_at desc
            "#,
        )
        .bind(team_id)
        .fetch_all(pool)
        .await?
    };

    Ok(rows.iter().map(map_workflow_row).collect())
}

pub async fn get_compliance_workflow(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
) -> Result<Option<ComplianceWorkflowRow>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select
            id,
            team_id,
            run_id,
            state,
            created_at,
            updated_at,
            created_by,
            updated_by
        from public.compliance_workflow
        where team_id = $1 and run_id = $2
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| map_workflow_row(&r)))
}

pub async fn transition_workflow_review(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
    user_id: Uuid,
    approve: bool,
) -> Result<Option<ComplianceWorkflowRow>, sqlx::Error> {
    let new_state = if approve { "approved" } else { "rejected" };
    let row = sqlx::query(
        r#"
        update public.compliance_workflow
        set
            state = $4,
            updated_at = now(),
            updated_by = $3
        where team_id = $1
          and run_id = $2
          and state = 'pending_review'
        returning
            id,
            team_id,
            run_id,
            state,
            created_at,
            updated_at,
            created_by,
            updated_by
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .bind(user_id)
    .bind(new_state)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| map_workflow_row(&r)))
}

pub async fn transition_workflow_promotion(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
    user_id: Uuid,
    allow: bool,
) -> Result<Option<ComplianceWorkflowRow>, sqlx::Error> {
    let new_state = if allow {
        "promotion_allowed"
    } else {
        "promotion_blocked"
    };
    let row = sqlx::query(
        r#"
        update public.compliance_workflow
        set
            state = $4,
            updated_at = now(),
            updated_by = $3
        where team_id = $1
          and run_id = $2
          and state = 'approved'
        returning
            id,
            team_id,
            run_id,
            state,
            created_at,
            updated_at,
            created_by,
            updated_by
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .bind(user_id)
    .bind(new_state)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| map_workflow_row(&r)))
}

pub async fn insert_identity_audit_log(
    pool: &DbPool,
    team_id: Uuid,
    actor_user_id: Uuid,
    action: &str,
    object_type: &str,
    object_id: &str,
    details: serde_json::Value,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.identity_audit_log
          (team_id, actor_user_id, action, object_type, object_id, details)
        values
          ($1, $2, $3, $4, $5, $6)
        "#,
    )
    .bind(team_id)
    .bind(actor_user_id)
    .bind(action)
    .bind(object_type)
    .bind(object_id)
    .bind(details)
    .execute(pool)
    .await?;
    Ok(())
}

/// Recent identity / governance audit rows for a team (tenant console).
pub async fn list_identity_audit_for_team(
    pool: &DbPool,
    team_id: Uuid,
    limit: i64,
) -> Result<Vec<serde_json::Value>, sqlx::Error> {
    use chrono::SecondsFormat;
    let rows = sqlx::query(
        r#"
        select action, object_type, object_id, details, ts
        from public.identity_audit_log
        where team_id = $1
        order by ts desc
        limit $2
        "#,
    )
    .bind(team_id)
    .bind(limit)
    .fetch_all(pool)
    .await?;

    let mut out = Vec::new();
    for r in rows {
        let ts: DateTime<Utc> = r.get("ts");
        out.push(serde_json::json!({
            "action": r.get::<String, _>("action"),
            "object_type": r.get::<String, _>("object_type"),
            "object_id": r.get::<String, _>("object_id"),
            "details": r.get::<serde_json::Value, _>("details"),
            "ts": ts.to_rfc3339_opts(SecondsFormat::Millis, true),
        }));
    }
    Ok(out)
}

pub async fn create_workflow_delegation(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
    scope: &str,
    delegator_user_id: Uuid,
    delegatee_user_id: Uuid,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.compliance_workflow_delegations
          (team_id, run_id, scope, delegator_user_id, delegatee_user_id)
        values
          ($1, $2, $3, $4, $5)
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .bind(scope)
    .bind(delegator_user_id)
    .bind(delegatee_user_id)
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn has_workflow_delegation(
    pool: &DbPool,
    team_id: Uuid,
    run_id: &str,
    scope: &str,
    delegatee_user_id: Uuid,
) -> Result<bool, sqlx::Error> {
    let row = sqlx::query_scalar::<_, i64>(
        r#"
        select 1
        from public.compliance_workflow_delegations
        where team_id = $1
          and run_id = $2
          and scope = $3
          and delegatee_user_id = $4
        limit 1
        "#,
    )
    .bind(team_id)
    .bind(run_id)
    .bind(scope)
    .bind(delegatee_user_id)
    .fetch_optional(pool)
    .await?;
    Ok(row.is_some())
}
