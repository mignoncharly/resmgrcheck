# Global navigation before/after evidence

These are actual local Chromium captures of authorized Django route responses
from disposable database-backed fixtures. They contain no production session,
password, access code, native run or service verdict. The rejected navigation run
fixture has no native execution or evidence; it exists only to exercise navigation.

Before captures load the original committed8ef2707 base/mobile/project templates
and CSS. After captures use this navigation implementation. Check JSONs distinguish
JavaScript accessibility scans from no-JS views. Browser screenshots are taken
after focus checks, with the skip link blurred to avoid covering the page header.
Restricted-code browser journeys are recorded in after-checks.json; their screenshots
are not saved. Test clients validate backend authorization independently of browser
rendering and intercept only locally fetched authorized HTML for browser clicks.

| View | Before | After |
| --- | --- | --- |
| Projects desktop | [before](before-project-1440.png) | [after](after-project-1440.png) |
| Projects mobile/no-JS | [before](before-project-390-no-js.png) | [after](after-project-390-no-js.png) |
| Run desktop | [before](before-run-1440.png) | [after](after-run-1440.png) |
| Run mobile/no-JS | [before](before-run-390-no-js.png) | [after](after-run-390-no-js.png) |

Additional tablet900 and small-mobile320 views are retained alongside these files.
Reproduce after checks using the staging wrapper:
`manage.py test tests.test_navigation --noinput`.
Before reproduction requires the original committed templates/CSS; the test's
RMC_NAV_CAPTURE=before mode reads HEAD and must be run from the original checkpoint
with the test supplied separately, as it was during implementation.
