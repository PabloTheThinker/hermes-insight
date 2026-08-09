# Experience layer (v0.6)

How any Hermes agent turns **tasks and events** into durable pattern memory — and recalls it faster next time.

## Why

Fabric index + cycle alone are strong on *structure* but weak on *lived time*. Agents rediscover the same failure class every session.

The experience layer adds:

| Concept | Kind | Role |
|---------|------|------|
| Event | `event` | One observation / incident / decision |
| Episode | `episode` | Multi-step arc or session slice |
| Task | `task` | Open/closed work unit with `task_id` |
| Links | `experienced_as`, `instance_of`, `next` | Event→pattern and temporal chain |

## Agent loop

```text
recall(query)  →  open_task  →  experience*  →  close_task
                      │              │
                      └──── connect ─┘
```

1. **recall** — hybrid match + experience echoes + neighbor hops + lever brief  
2. **open_task** — seeds starters if empty; returns priors + `task_id`  
3. **experience** — catalogues body, auto-links top structural matches, chains `next` within task  
4. **close_task** — outcome episode; reinforces matched patterns on success  

## Tools (plugin)

- `insight_recall`
- `insight_experience`
- `insight_task` (`open`|`close`)
- `insight_connect`
- `insight_bootstrap`
- `insight_ingest_messages`

## Install any agent

```bash
./scripts/install_for_hermes.sh
HERMES_HOME=~/.hermes/profiles/foo ./scripts/install_for_hermes.sh --agent foo
```

## Privacy

Experiences are scrubbed via `scrub_text`. Still: separate DBs per client/compartment.
