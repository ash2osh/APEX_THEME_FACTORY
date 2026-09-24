# Release test app

`minimal/` is the disposable consumer app used by `scripts/theme.sh release`: app **9010**, alias
`TF-CONSUMER-MINIMAL-9010` in workspace `DEMO`.

- Universal Theme 42 / `ut-26.1` / Iris, side navigation, a static navigation bar with user menu and sign-out.
- One public page (Page 1 `Home`), no Global Page, no static files — so an install creates Page 0 and an
  uninstall returns to zero footprint.

Create or reset it with `scripts/reset-consumer.sh` (IDs are restricted to 9000–9099; it never overwrites an app
with a different alias).
