# Home Assistant blueprints

Custom automation blueprints, tracked here and copied into Home Assistant by
hand. One file per blueprint, no shared code.

## LIFX switches

Almost all loads here are dumb fittings on LIFX relays, so the relay *is*
the light. That makes most of this unnecessary — see "Which buttons need an
automation".

### Blueprints

**`lifx_button.yaml`** — the only one you need. One instance per physical
button that requires HA involvement.

An earlier design collapsed everything into a single router automation. It
works, but the trigger entity lists have to duplicate the mapping table by
hand and a mismatch fails silently. Not worth it — hence one instance per
button.

### Which buttons need an automation

**Most don't.** A dumb load on its own attached relay, pressed by its own
button, needs nothing. Hardware toggles it, HA observes the relay, group
membership and schedules already reach it.

Create an instance only for:

| Situation | Setup |
|---|---|
| Button controls something other than its own relay | `authority` = that entity, `wired: false` |
| Button controls a group | `authority` = a switch-group helper, `wired: false` |
| Button needs a double or long press gesture | `authority` = whatever it controls, gestures filled in |
| Button toggles its own load *and* brings the room along | `wired: true`, `followers` = the other relays |
| A spare or detached gang should display another light's state | `indicators` = that relay |

### Inputs

| Input | Meaning |
|---|---|
| `button` | The `event.*` entity for this one button |
| `authority` | The entity holding the true state |
| `wired` | True only if this button switches the authority in hardware |
| `indicators` | Display-only relays. Always forced to match, including at hourly heal |
| `followers` | Real lights moved when the authority changes, then left alone |
| `double_target` | Toggled on double press |
| `long_press_actions` | Free-form actions on long press |

`indicators` vs `followers` is a policy choice. An indicator that disagrees
is wrong and gets corrected. A follower may have been changed for a good
reason — a scene, a schedule — so it is never re-asserted at heal. Slave a
light strictly by listing it as an indicator.

### Things to be careful of

**Getting `wired` wrong.** True on a button that isn't hard-wired: it
predicts a change that never happens and the room flaps until the next
reconcile. False on one that is: the press toggles the load in hardware
*and* the automation toggles it again — the double-toggle race. Neither
throws an error.

**Indicators must not be loads.** Only a spare or detached gang can be an
indicator. A relay driving a fitting cannot also be a display; writing to
it switches something.

**Never list the authority in `indicators` or `followers`.** Harmless in
practice — the difference guard can't fire — but it means the two roles
have been confused, and the next edit is where that bites.

**Group control: make the group the authority.** Don't point `authority` at
one member relay with the others as followers. That makes it the master, so
its own local button drags the whole group along.

**Duplicate `indicators` and `followers` deliberately.** Mirroring triggers
on the authority's state, so it fires from whichever instance holds it. Put
the same lists on every button instance for that authority. Extra copies
cost one guarded no-op run each and mean no instance is secretly
load-bearing for another.

**Use `homeassistant.toggle`, never `light.toggle`.** Relays are `switch.`
entities; `light.toggle` rejects them.

**Rename opaque entity IDs** before writing instances. IDs like
`light.0x001788010c2ed0f2` end up in every instance, dashboard and log line.

### Optional

`switch_as_x` (Settings → Devices & Services → Helpers → *Change device type
of a switch*) republishes a relay as a `light` entity, so it joins light
groups and HomeKit's "turn off all lights". Useful for tidiness; not
required, since group-level automations already hit the relays directly.
If you do it, point blueprint inputs at the new `light.` entity — the
original is hidden but still changes state.

## Installing

**The blueprint importer does not work against this repo while it is
private** — it fetches HTML and fails with a YAML error pointing at CSS.
Copy the file in directly instead:

```bash
cp lifx_button.yaml /path/to/config/blueprints/automation/local/
```

Then Developer Tools → YAML → *Reload blueprints*. Existing automations
built on a blueprint pick up the new version on reload; no need to recreate
them.

## Checking a blueprint before copying it

```bash
pip install pyyaml
python3 scripts/validate.py *.yaml
```

Catches syntax errors and missing top-level keys. It cannot check selectors,
templates or action schemas — those only fail in Home Assistant, so still
reload and press the button.
