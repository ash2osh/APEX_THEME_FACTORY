Thin adapter around APEX JavaScript APIs (spec §66): `items.js`, `server.js`, `regions.js`, `events.js`
exposing `App.apex.items / server / regions / events`. Create a file only when two components need the
same wrapper; otherwise call `apex.*` directly (see skill apex-alpine-server-integration).
