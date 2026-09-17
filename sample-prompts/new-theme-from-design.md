Turn a design into a portable Theme Factory theme package.

**Boundary:** APEX 26.1.x · Universal Theme 42 · theme style **Iris** only. The design is reinterpreted *onto*
Universal Theme — Universal Theme owns structure, the theme package owns appearance. Never switch theme
styles, never use Theme Roller, never replace a native component with custom markup to match a mockup.
**Blast radius:** edits source under `sample-themes/<name>/` and builds a ZIP into `dist/`. It does **not**
import into any database — ask me if you think an import is needed.
**Browser access:** only through the project daemon —
`python3 tools/chrome_devtools_client.py <tool> '<json-args>'`.

## My design

- Source: << Figma link | screenshot path | URL to copy the feel of | written direction >>
- Theme name (lowercase, hyphenated): << name >>
- Light or dark: << light | dark >>
- What matters most about it: << the one or two qualities that must survive, e.g. "calm, lots of white space,
  colour only on actions" >>

## Do this

Read `AGENTS.md` and route through `.agents/skills/design-to-apex/SKILL.md`; follow its workflow in order and
load only the skills each step needs. Before writing any CSS, read `.agents/knowledge/pitfalls.md` §1.

1. **Understand** the design. Split it into header, navigation, content surfaces, data components, actions,
   dialogs. Say what you are *not* going to reproduce, and why — a design that fights Universal Theme's
   structure should be adapted, not forced.
2. **Inspect the runtime first.** Open the reference app and read the real DOM and computed styles for the
   components the design touches. Writing CSS before this is the project's most common failure.
3. **Extract tokens, not screenshots.** Map the design's colours, spacing, radii and type onto the `--app-*`
   roles in `static-files/css/foundation/tokens.css`. Add a default there before using a new role. A
   theme-private palette may use its own short prefix.
4. **Scaffold** by copying the closest existing package (`linen` for light, `solarized-dark` for dark) and
   renaming the class in `theme.json` and every selector.
5. **Write `css/tokens.css`**, then map onto Universal Theme's own atoms on the theme-style scope
   (`.app-theme-<name> .apex-theme-iris`) — never at `:root`.
6. **Write component rules** in `css/apex/*.css`: every selector prefixed with the package class, no literal
   colours, `!important` only to mirror an Iris `!important` with the Iris rule quoted in a comment.
7. **See it for real:** `scripts/sync-static.sh`, then `scripts/apex-validate.sh`. Tell me if an import is
   needed to view it — do not run one yourself.
8. **Audit accessibility before claiming anything.** Run the contrast sweep from `docs/CHROME_DEVTOOLS_MCP.md`
   and drive the states a resting sweep cannot see: select a report row, open a date picker, hover a toolbar,
   open a dialog, empty a search box. For a dark theme also read `harden-dark-theme.md` — three Universal Theme
   token families freeze at `:root` and will bite you.
9. **Write the package README** with the direction, the technique, and a *Verified* section listing exactly
   which pages, widths and states you measured.
10. **Build:** `scripts/package-theme.sh <name>`.

## Report

- The token table you derived, and where you deliberately departed from the design to keep AA contrast or to
  respect Universal Theme's structure.
- The measured contrast numbers, with the count of nodes scanned — `0 failures` alone is not evidence.
- What you did **not** cover: pages unopened, widths untested, states undriven.
- The built ZIP path and its SHA-256.
