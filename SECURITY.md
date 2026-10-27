# Security policy

QuakeNode is a **research testbed, not an operational warning system**. It must not be used to issue, suppress or inform
real alerts or safety decisions, so a flaw in it is not a safety-critical vulnerability in the usual sense. It reads YAML
configs and (optionally) local data files and writes files into directories you choose.

## Supported versions

Only the latest released version (currently 0.2.x) receives fixes.

## Reporting a vulnerability

Please report privately, not in a public issue: use the repository's security advisory form
(`https://github.com/vincentvega011/quakenode/security/advisories/new`) or the
maintainers' address yajan.adh@gmail.com. Include the version, a minimal reproduction (a config or input
file) and the impact you see. Reports of unsafe file handling (for example configs that write outside the chosen output
directory), unsafe deserialisation, or dependency vulnerabilities are welcome.

We aim to acknowledge a report within a week; this is a volunteer research project, so there is no response-time guarantee.
