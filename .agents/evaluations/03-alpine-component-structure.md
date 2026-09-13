# Evaluation: Alpine Component Structure
Given: a reusable stateful component (picker, stepper, panel).
Expected: `Alpine.data('name', …)` in `static-files/js/components/<name>.js`, small `x-data="name({…})"` in markup, contract added to docs/COMPONENTS.md.
Failure: 100 lines of JavaScript inside `x-data`, business logic in the component, no contract.
Skills under test: apex-alpine-components.
