from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('control','0009_optional_ai')]
    operations=[migrations.RunSQL('''
      CREATE FUNCTION control_ai_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF (SELECT project_id FROM control_run WHERE id=NEW.run_id) IS DISTINCT FROM
           (SELECT project_id FROM control_sourcesubmission WHERE id=NEW.source_id) AND NEW.source_id IS NOT NULL
        THEN RAISE EXCEPTION 'AI source tenant mismatch'; END IF;
        IF NEW.compared_run_id IS NOT NULL AND (SELECT project_id FROM control_run WHERE id=NEW.run_id) IS DISTINCT FROM
           (SELECT project_id FROM control_run WHERE id=NEW.compared_run_id)
        THEN RAISE EXCEPTION 'AI comparison tenant mismatch'; END IF;
        IF TG_OP='UPDATE' AND
          (NEW.run_id,NEW.actor_id,NEW.source_id,NEW.compared_run_id,NEW.actor_auth_hash,NEW.mfa_at,NEW.idempotency_key,NEW.task,
           NEW.input_sha256,NEW.provider,NEW.requested_model,NEW.pricing,NEW.reserved_microusd,NEW.consent_version)
          IS DISTINCT FROM
          (OLD.run_id,OLD.actor_id,OLD.source_id,OLD.compared_run_id,OLD.actor_auth_hash,OLD.mfa_at,OLD.idempotency_key,OLD.task,
           OLD.input_sha256,OLD.provider,OLD.requested_model,OLD.pricing,OLD.reserved_microusd,OLD.consent_version)
        THEN RAISE EXCEPTION 'AI consent identity is immutable'; END IF;
        IF TG_OP='UPDATE' AND (NEW.payload,NEW.citations) IS DISTINCT FROM (OLD.payload,OLD.citations)
           AND NOT (OLD.erased_at IS NULL AND NEW.erased_at IS NOT NULL AND NEW.payload='{}'::jsonb AND NEW.citations='{}'::jsonb)
        THEN RAISE EXCEPTION 'AI consent payload is immutable except erasure'; END IF;
        IF TG_OP='UPDATE' AND OLD.erased_at IS NOT NULL AND (NEW.payload,NEW.result,NEW.citations) IS DISTINCT FROM ('{}'::jsonb,'{}'::jsonb,'{}'::jsonb)
        THEN RAISE EXCEPTION 'Erased AI data cannot be restored'; END IF;
        RETURN NEW;
      END; $$;
      CREATE TRIGGER control_ai_immutable BEFORE INSERT OR UPDATE ON control_aianalysis
      FOR EACH ROW EXECUTE FUNCTION control_ai_intent_guard();
    ''','DROP TRIGGER control_ai_immutable ON control_aianalysis; DROP FUNCTION control_ai_intent_guard();')]
