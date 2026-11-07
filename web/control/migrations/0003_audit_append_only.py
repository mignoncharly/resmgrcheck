from django.db import migrations
SQL='''
CREATE FUNCTION control_audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Audit events are append-only'; END; $$;
CREATE TRIGGER control_audit_no_update_delete BEFORE UPDATE OR DELETE ON control_auditevent
FOR EACH ROW EXECUTE FUNCTION control_audit_append_only();
'''
REVERSE='DROP TRIGGER control_audit_no_update_delete ON control_auditevent; DROP FUNCTION control_audit_append_only();'
class Migration(migrations.Migration):
    dependencies=[('control','0002_ratebucket_user_session_version_accountdeletion_and_more')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
