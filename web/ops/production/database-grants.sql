-- Execute ONLY as resmgr_owner on the dedicated resmgrcheck_web database after migrations.
-- Runtime roles own no relations and cannot disable immutable/audit triggers.
\set ON_ERROR_STOP on
REVOKE ALL ON DATABASE resmgrcheck_web FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE resmgrcheck_web TO resmgr_web,resmgr_exec,resmgr_ai,resmgr_backup;
GRANT USAGE ON SCHEMA public TO resmgr_web,resmgr_exec,resmgr_ai,resmgr_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO resmgr_web,resmgr_exec,resmgr_ai,resmgr_backup;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO resmgr_web,resmgr_exec,resmgr_ai;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO resmgr_backup;
REVOKE ALL ON SEQUENCE control_runnernonce_id_seq,control_runnerchunk_id_seq FROM resmgr_exec,resmgr_ai;
GRANT INSERT ON control_auditevent TO resmgr_web,resmgr_exec,resmgr_ai;
GRANT INSERT,UPDATE,DELETE ON
 control_user,control_organization,control_membership,control_project,control_projectmembership,
 control_ratebucket,control_accesscode,control_accessgrant,control_accessgrant_targets,
 control_accessgrant_evidence,control_accesssession,control_target,control_buildrelease,
 control_run,control_sourcesubmission,control_aianalysis,control_aiusage,
 django_session,control_cache,account_emailaddress,account_emailconfirmation,
 mfa_authenticator,usersessions_usersession TO resmgr_web;
GRANT INSERT,UPDATE ON control_customerrunner,control_runnerenrollment,control_runnerjob TO resmgr_web;
GRANT INSERT,DELETE ON control_runnernonce TO resmgr_web;
GRANT INSERT ON control_runnerchunk TO resmgr_web;
GRANT INSERT,UPDATE ON control_run,control_target,control_executorslot,control_artifact,
 control_sourcesubmission,control_aianalysis TO resmgr_exec;
GRANT UPDATE ON control_runnerjob TO resmgr_exec;
GRANT DELETE ON control_runnerchunk TO resmgr_exec;
GRANT DELETE ON control_ratebucket TO resmgr_exec;
GRANT INSERT,UPDATE ON control_aianalysis,control_aiproviderstate,control_aiusage,control_ailease TO resmgr_ai;
-- No runtime schema CREATE, relation ownership, role membership, DDL or audit rewrite.
