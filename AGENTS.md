# AGENTS.md — Wrike Timer

## Données sensibles — ne jamais partager

- Le token API Wrike (Permanent Access Token) ne doit **jamais** apparaître dans le code, un commit, un message de commit, une issue/PR, un log, ou une réponse d'agent. Il vit uniquement dans le trousseau système (keyring) ou, en fallback si aucun backend keyring n'est disponible, dans `~/.config/wrike-timer/config.json` (chmod 600, jamais commité).
- Ne jamais committer `config.json`, `state.json`, ou `*.log` : ils peuvent contenir des titres de tâches, des IDs Wrike, ou des données de temps qui appartiennent à l'organisation Wrike de l'utilisateur, pas au repo.
- Les logs ne contiennent que ce qui est nécessaire au debug (task ID, durée, code HTTP) — jamais le corps complet d'une réponse API, une description de tâche, ni le token.
- Pour du debug avec de vraies données API, ne pas coller de réponse brute contenant des données réelles dans un fichier versionné ou un message partagé ; utiliser des données factices dans les tests.
- `config.example.json` ne doit contenir que des valeurs placeholder, jamais une vraie URL/token — un hook pre-commit local le vérifie (voir README, section Sécurité).

## Capture d'écran du menu tray

Pour illustrer une évolution du menu (README, doc, PR) sans vrai token ni vraies données Wrike : `.venv/bin/python scripts/fake_tray_screenshot.py` affiche le tray avec un chrono actif et des tickets factices. Voir README, section Développement.

## Règles agents (toujours)

- **Think before coding** : Don't assume. Don't hide confusion. Surface tradeoffs. If uncertain, ask.
- **Keep It Stupid Simple** : Minimum code that solves the problem. Nothing speculative.
- **Surgical changes** : Touch only what you must. Clean up only your own mess.
- **Goal-Driven execution** : Define success criteria. Loop until verified.
- **Kaizen** : Continuous Improvement. After all changes are done, re-read your modification and see if there is a better way to do it: smaller, faster, smarter considering the whole project. Also see if what you learnt during this session can help improve or fix other parts of the project.

**These guidelines are working if**: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, clarifying questions come before implementation rather than after mistakes, and we learn from our mistakes.
