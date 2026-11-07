from django.db import migrations

SQL='''
CREATE FUNCTION control_code_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.id,NEW.verifier,NEW.organization_id,NEW.created_by_id) IS DISTINCT FROM (OLD.id,OLD.verifier,OLD.organization_id,OLD.created_by_id)
 THEN RAISE EXCEPTION 'Issued code identity/verifier is immutable'; END IF;
 IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at
 THEN RAISE EXCEPTION 'Code revocation is irreversible'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_code_identity BEFORE UPDATE ON control_accesscode FOR EACH ROW EXECUTE FUNCTION control_code_identity_guard();
CREATE FUNCTION control_session_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.code_id,NEW.browser_key_hash,NEW.policy_version) IS DISTINCT FROM (OLD.code_id,OLD.browser_key_hash,OLD.policy_version)
 THEN RAISE EXCEPTION 'Browser session identity is immutable'; END IF;
 IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS NULL THEN RAISE EXCEPTION 'Session revocation is irreversible'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_session_identity BEFORE UPDATE ON control_accesssession FOR EACH ROW EXECUTE FUNCTION control_session_identity_guard();
CREATE FUNCTION control_grant_target_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT project_id FROM control_target WHERE id=NEW.target_id) IS DISTINCT FROM (SELECT project_id FROM control_accessgrant WHERE id=NEW.accessgrant_id)
 THEN RAISE EXCEPTION 'Granted target project mismatch'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_granted_target BEFORE INSERT OR UPDATE ON control_accessgrant_targets FOR EACH ROW EXECUTE FUNCTION control_grant_target_guard();
CREATE FUNCTION control_grant_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT project_id FROM control_run WHERE id=NEW.run_id) IS DISTINCT FROM (SELECT project_id FROM control_accessgrant WHERE id=NEW.accessgrant_id)
 THEN RAISE EXCEPTION 'Granted evidence project mismatch'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_granted_evidence BEFORE INSERT OR UPDATE ON control_accessgrant_evidence FOR EACH ROW EXECUTE FUNCTION control_grant_evidence_guard();
'''
class Migration(migrations.Migration):
    dependencies=[('control','0016_administrator_only_accounts')]
    operations=[migrations.RunSQL(SQL,'''
      DROP TRIGGER control_code_identity ON control_accesscode; DROP FUNCTION control_code_identity_guard();
      DROP TRIGGER control_session_identity ON control_accesssession; DROP FUNCTION control_session_identity_guard();
      DROP TRIGGER control_granted_target ON control_accessgrant_targets; DROP FUNCTION control_grant_target_guard();
      DROP TRIGGER control_granted_evidence ON control_accessgrant_evidence; DROP FUNCTION control_grant_evidence_guard();
    ''')]
