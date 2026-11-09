-- Additive permissions only, on the dedicated resmgrcheck_web database.
GRANT SELECT ON control_customerrunner,control_runnerenrollment,control_runnernonce,control_runnerjob,control_runnerchunk TO resmgr_web,resmgr_exec,resmgr_ai,resmgr_backup;
GRANT INSERT,UPDATE ON control_customerrunner,control_runnerenrollment,control_runnerjob TO resmgr_web;
GRANT INSERT,DELETE ON control_runnernonce TO resmgr_web;
GRANT INSERT ON control_runnerchunk TO resmgr_web;
GRANT USAGE,SELECT ON SEQUENCE control_runnernonce_id_seq,control_runnerchunk_id_seq TO resmgr_web;
GRANT SELECT ON SEQUENCE control_runnernonce_id_seq,control_runnerchunk_id_seq TO resmgr_backup;
GRANT UPDATE ON control_runnerjob TO resmgr_exec;
GRANT DELETE ON control_runnerchunk TO resmgr_exec;
