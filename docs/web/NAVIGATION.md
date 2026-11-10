# Shared application navigation

Navigation is defined once in control/templatetags/navigation.py. The base template
builds one model using the resolved named route, authorized view objects and
existing project/run/source/analysis/organization permission checks. Named Django
URLs supply all destinations. Desktop and mobile use the same app_menu partial;
the navigation partial renders breadcrumbs and contextual returns outside narrow
account-form wrappers. Parent links work on direct URL access and refresh without
history or JavaScript. There are no arbitrary next/return URLs.

| Area | Parents and returns |
| --- | --- |
| Overview, lists | Dashboard breadcrumb; persistent section menu |
| Project details | Dashboard / Projects / Project; Back to Projects |
| Project targets and builds | Project and Projects; all targets; target operations and runners also link project targets |
| New run, project permissions | Project and Projects; membership assignment remains in project details, with no invented GET editor |
| Run details and replay | Project, Projects and project run history; replay/analysis also return to the exact run |
| Compare | Compare section remains active; a same-project selected comparison also links its authorized project |
| Project AI/source | Project and Projects; analysis returns to its exact run; protected error pages resolve authorized parents by ID |
| Organization/team/audit/retention | Account security, actual team page and authorized organization scope |
| Access codes and sessions | Organization team and access-code list; no administrator links for code principals |
| Account/password/browser sessions | Account security parent; code principal's account link goes to its own access session |
| Recorded demo/documentation | Shared authenticated menu remains present; public/anonymous menus are retained |

Organization names have no invented landing route and appear as scope labels.
Only actual parent pages get hyperlinks. Leaf pages have aria-current=page;
sidebar/mobile active sections are derived from route families rather than
inconsistent per-view page flags. Targets and runner descendants keep Targets
active; runs/replay/analysis keep Test runs active; project settings/source keep
Projects active; organization/account administration keeps Account & security.

Project run history uses the existing run_history route with a validated project
UUID. It calls project_access and filters the already authorized visible_runs
queryset. State/service filters remain within that scope. Run-table links carry
only filter values, and contextual returns accept only the existing allowed
states/adapters, encoded as query parameters. Clearing filters retains the project.
No stored session, cross-origin destination or browser history is used for returns.

Downloads, API/machine responses and immutable standalone evidence documents are
not application navigation screens. Evidence remains unchanged in its existing
dashboard frame or download. POST-only actions remain actions, not invented parent
destinations. Existing view authorization, CSRF, audit, queue and runner semantics
remain authoritative; navigation does not grant any new permissions.

Verification covers real database-backed administrator and restricted-code routes,
foreign/invalid project filters, revoked authority, direct links and refresh.
Local Chromium replays actual authorized HTML fetched through those Django routes;
its parent/dashboard clicks use the real named paths and replay the corresponding
authorized response. External scripts are omitted and repository CSS/axe injected
for isolated rendering. Browser checks are not production HTTP/UAT qualification.
Project and run screenshots cover1440/900/390/320px with JavaScript on/off;
restricted-code browser journeys use the same widths without saving code secrets.
See evidence/global-navigation and TEST_EVIDENCE W039 for actual outcomes.

No production deployment occurs in this change. The prior W038 driver remains
pinned to the earlier security-page candidate and cannot deploy these new bytes.
Any later deployment must stage a newly reviewed immutable application candidate
through the existing backup/restore/private-runtime/activation/recovery procedure.
