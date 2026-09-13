# Evaluation: APEX Refresh
Given: an Alpine component inside a region that is refreshed by a Dynamic Action.
Expected: component works after `apexafterrefresh`; no duplicate handlers; no `Alpine.start()` re-call; state re-synced from the APEX item.
Failure: duplicate handlers, broken state, repeated Alpine startup, stale DOM references.
Skills under test: apex-alpine-lifecycle.
