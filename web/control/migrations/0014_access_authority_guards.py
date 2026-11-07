from django.db import migrations

def disable_unprovisioned(apps,schema_editor):
    # Preserve every identity/foreign key/audit row. No old password account is
    # silently elevated. An operator may explicitly adopt it through provisioning.
    from django.db.models import F
    users=apps.get_model('control','User').objects.filter(username__isnull=True)
    identifiers=list(users.values_list('id',flat=True))
    users.update(is_active=False,session_version=F('session_version')+1)
    for identifier in identifiers:
        apps.get_model('control','AuditEvent').objects.create(action='access_model.legacy_account_disabled',object_id=str(identifier),details={'local_provisioning_required':True})

SQL='''
CREATE FUNCTION control_access_principal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE principal_code uuid;
BEGIN
 IF TG_OP='UPDATE' AND NEW.access_session_id IS DISTINCT FROM OLD.access_session_id
 THEN RAISE EXCEPTION 'Access session job identity is immutable'; END IF;
 IF TG_OP='INSERT' AND NEW.access_session_id IS NOT NULL THEN
   SELECT s.code_id INTO principal_code FROM control_accesssession s WHERE s.id=NEW.access_session_id;
   IF NOT EXISTS(SELECT 1 FROM control_accessgrant g WHERE g.code_id=principal_code AND g.project_id=NEW.project_id)
   THEN RAISE EXCEPTION 'Access principal project mismatch'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_run_access_identity BEFORE INSERT OR UPDATE ON control_run
FOR EACH ROW EXECUTE FUNCTION control_access_principal_guard();
CREATE TRIGGER control_source_access_identity BEFORE INSERT OR UPDATE ON control_sourcesubmission
FOR EACH ROW EXECUTE FUNCTION control_access_principal_guard();
CREATE FUNCTION control_ai_access_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE principal_code uuid; scope_project uuid;
BEGIN
 IF TG_OP='UPDATE' AND NEW.access_session_id IS DISTINCT FROM OLD.access_session_id
 THEN RAISE EXCEPTION 'AI access session identity is immutable'; END IF;
 IF TG_OP='INSERT' AND NEW.access_session_id IS NOT NULL THEN
   SELECT s.code_id INTO principal_code FROM control_accesssession s WHERE s.id=NEW.access_session_id;
   SELECT r.project_id INTO scope_project FROM control_run r WHERE r.id=NEW.run_id;
   IF NOT EXISTS(SELECT 1 FROM control_accessgrant g WHERE g.code_id=principal_code AND g.project_id=scope_project)
   THEN RAISE EXCEPTION 'AI access principal project mismatch'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_ai_access_identity BEFORE INSERT OR UPDATE ON control_aianalysis
FOR EACH ROW EXECUTE FUNCTION control_ai_access_guard();
CREATE FUNCTION control_grant_tenant_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT organization_id FROM control_project WHERE id=NEW.project_id) IS DISTINCT FROM
    (SELECT organization_id FROM control_accesscode WHERE id=NEW.code_id)
 THEN RAISE EXCEPTION 'Access grant organization mismatch'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_grant_tenant BEFORE INSERT OR UPDATE ON control_accessgrant
FOR EACH ROW EXECUTE FUNCTION control_grant_tenant_guard();
'''

class Migration(migrations.Migration):
    dependencies=[('control','0013_administrator_access_codes')]
    operations=[migrations.RunPython(disable_unprovisioned,migrations.RunPython.noop),migrations.RunSQL(SQL,'''
      DROP TRIGGER control_run_access_identity ON control_run; DROP TRIGGER control_source_access_identity ON control_sourcesubmission;
      DROP TRIGGER control_ai_access_identity ON control_aianalysis; DROP TRIGGER control_grant_tenant ON control_accessgrant;
      DROP FUNCTION control_access_principal_guard(); DROP FUNCTION control_ai_access_guard(); DROP FUNCTION control_grant_tenant_guard();
    ''')]
