# Security

Please report a security problem privately through
[GitHub private vulnerability reporting](https://github.com/ash2osh/APEX_THEME_FACTORY/security/advisories/new),
not in a public issue. Include the theme or script, your APEX version, and the steps that show the problem.

This is a volunteer project, so there is no response-time promise, and fixes go into the latest release only.

## What to keep in mind

- **Install packages only from a source you trust.** A package runs Python on your machine and adds a script to
  every page of your app. A checksum proves that a file is complete. It does not prove who made it.
- **Keep `theme-factory-backups/` private.** A backup holds your app's full source, including its session-state
  protection salt.
- **The browser daemons are development tools.** Run them on your own machine only. Don't expose their sockets or
  ports to a network.
