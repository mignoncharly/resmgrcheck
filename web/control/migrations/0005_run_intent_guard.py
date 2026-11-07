from django.db import migrations
SQL='''
CREATE FUNCTION control_run_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT project_id FROM control_target WHERE id=NEW.target_id) IS DISTINCT FROM NEW.project_id THEN
  RAISE EXCEPTION 'Run target tenant mismatch'; END IF;
 IF NEW.build_id IS NOT NULL AND (SELECT target_id FROM control_buildrelease WHERE id=NEW.build_id) IS DISTINCT FROM NEW.target_id THEN
  RAISE EXCEPTION 'Run build target mismatch'; END IF;
 IF NEW.original_id IS NOT NULL AND (SELECT project_id FROM control_run WHERE id=NEW.original_id) IS DISTINCT FROM NEW.project_id THEN
  RAISE EXCEPTION 'Replay tenant mismatch'; END IF;
 IF TG_OP='UPDATE' AND
 (NEW.project_id,NEW.target_id,NEW.build_id,NEW.actor_id,NEW.native_run_id,NEW.operation,NEW.original_id,NEW.profile,NEW.suite,NEW.fixture_mode,NEW.idempotency_key,NEW.intent_sha256,NEW.actor_auth_hash,NEW.mfa_at)
 IS DISTINCT FROM
 (OLD.project_id,OLD.target_id,OLD.build_id,OLD.actor_id,OLD.native_run_id,OLD.operation,OLD.original_id,OLD.profile,OLD.suite,OLD.fixture_mode,OLD.idempotency_key,OLD.intent_sha256,OLD.actor_auth_hash,OLD.mfa_at)
 THEN RAISE EXCEPTION 'Run intent is immutable'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_run_immutable BEFORE INSERT OR UPDATE ON control_run
FOR EACH ROW EXECUTE FUNCTION control_run_intent_guard();
'''
class Migration(migrations.Migration):
    dependencies=[('control','0004_buildrelease_run_executorslot_target_run_target_and_more')]
    operations=[migrations.RunSQL(SQL,'DROP TRIGGER control_run_immutable ON control_run; DROP FUNCTION control_run_intent_guard();')]
