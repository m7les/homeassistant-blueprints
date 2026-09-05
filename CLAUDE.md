# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A flat collection of Home Assistant **automation blueprints** (`blueprint.domain: automation`). Each `.yaml` file at the repo root is a standalone blueprint — no shared code, no package, no build step, no test suite. See `README.md` for the operational guide (which buttons need an automation, input semantics, failure modes).

Blueprints are installed by copying them into `<config>/blueprints/automation/local/` and reloading. The HA blueprint importer does **not** work against this repo while it is private: it fetches HTML and fails with a YAML error pointing at CSS.

## Commands

```bash
python3 scripts/validate.py *.yaml     # parse-check (needs pyyaml)
```

`scripts/validate.py` stubs out HA's `!input` tags, which PyYAML doesn't know, then checks each file parses and has `blueprint:`, triggers and actions. It cannot validate selectors, templates or action schemas — those only fail in Home Assistant. Real verification is: copy in, reload blueprints, press the button.

## The blueprint model

`lifx_button.yaml` is the sole blueprint and encodes the pattern to reuse.

**One instance per physical button.** Gestures are per button, so the instance is too. Mirroring hangs off the *authority's* state rather than off any button, so it fires no matter which instance holds it. This makes duplication safe and deliberate: the same `followers`/`indicators` lists go on every button instance for an authority, so no instance is secretly load-bearing for another.

**Authority / indicators / followers.** One entity holds the truth; everything else is driven one-way from it.

- `authority` — the light, light group, or (when a dumb load is hard-wired to a switch) the attached relay. **Optional**: the selector is `multiple: true` with `default: []` purely so it can be left empty, which yields a gesture-only button. It is normalised to a single entity id in `variables:`, tolerating the plain string that pre-existing instances stored, and every use of it is gated on `has_authority`.
- `indicators` — display-only detached relays. Always forced to match, including at start and hourly heal, because an indicator that disagrees is simply wrong.
- `followers` — real lights, moved when the authority *changes* and then left alone. Deliberately **not** re-asserted at heal, so a scene or a scheduled all-off isn't dragged back within the hour.

That indicator/follower split is the load-bearing design decision. Preserve it: the sync branch computes `targets` as `indicators` alone on `start`/`heal`, versus `followers + indicators` on a real authority change.

**`wired` decides command vs. predict.** False (default) → the button commands the authority with `homeassistant.toggle`. True → hardware already switched it, so the automation only *predicts* the outcome on followers and indicators; a wrong guess is corrected when the relay reports. Getting this backwards is the main failure mode and throws no error: `wired: true` on a non-wired button makes the room flap until reconcile; `wired: false` on a wired one gives the double-toggle race.

**Self-healing.** One shared branch serves three trigger ids — the authority's state change (`sync`), `homeassistant` start (`start`), and an hourly `time_pattern` (`heal`). Put new state-writing logic inside this branch rather than adding a parallel path.

**Tail reconcile.** A second top-level action after the `choose` runs on `single`/`double`/`long` only. It waits up to 3s for the authority to report, then re-asserts. This exists because `sync` cannot fire when the authority ends where it began — a double press consuming two toggles, a command that never landed — leaving a prediction uncorrected until the hourly heal. Keep it a *sibling* of the `choose`, never a branch inside it.

**Guarded writes, and the one deliberate exception.** Writes are guarded on the target being available and differing from `want`. Availability and difference are checked **separately and must stay that way**: indicators skip the difference half after a press (`force`, or `repeat.item in indicators` in the tail) because a detached relay toggles its own reported state when pressed, making that read stale exactly when it matters. They never skip the availability half — these are LIFX devices on UDP, the integration raises on timeout, and a raise inside `repeat` aborts the run, silently leaving every later target unwritten.

**`mode: parallel`, not `queued`.** The 3s tail wait would make a second press sit behind the first under `queued`. Writes are idempotent so concurrent runs converge; the later run wins.

**Startup delay.** `start` waits 60s (`{{ 60 if trigger.id == 'start' else 0 }}`) so integrations connect before any state is trusted.

**Concurrency.** `mode: queued`, `max: 10`, `max_exceeded: silent` — button spam is absorbed, not dropped loudly.

## Conventions

- Modern HA schema: `triggers:`/`actions:`, `- trigger: state`, `action: homeassistant.turn_on`. Not the legacy `trigger:`/`platform:`/`service:` spelling.
- Buttons are `domain: event` entities, triggered via `event.received` with an `event_type` filter. On builds lacking `event.received`, fall back to a `state` trigger with `not_to: ["unavailable", "unknown"]` and branch on `trigger.to_state.attributes.event_type`.
- `homeassistant.turn_on`/`turn_off`/`toggle`, never the `light.*` equivalents — relays are `switch.` entities and `light.toggle` rejects them.
- Filenames use underscores and match the path in each file's header comment.
- Quote any plain scalar containing `: ` (e.g. `description: "…(domain: event)"`). An unquoted colon-space is a parse error and was how a previous blueprint here silently failed to load.
