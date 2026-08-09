# Pattern Forge — how patterns become useful

Collecting patterns is half the work. Humans use patterns to:

| Mode | Product | Question |
|------|---------|----------|
| Orient | map | Where am I? |
| Predict | prediction board | What's coming? |
| Transfer | transfer pack | What shape reuses? |
| Invent | invention seeds | What new thing exists at the intersection? |
| Act | playbooks | What do I do Tuesday? |
| Watch | watch edges | What's rotting or orphaned? |

```bash
hermes-insight forge
hermes-insight forge --only invent,playbooks
```

Plugin: `insight_forge`

Outputs land in `<db-dir>/forged/<timestamp>/` with `LATEST` pointer.
Synthesis nodes write back into the lattice (`fabric: forge`).
