# Wrike Timer

Chrono de suivi de temps dans le tray système, qui parle uniquement à l'API Wrike — aucun service tiers, aucune donnée partagée avec Toggl/Clockify/etc.

Le menu liste les 10 derniers tickets sur lesquels tu as loggé du temps ; un clic démarre le chrono, un clic sur l'entrée active l'arrête et pousse le temps vers Wrike. Il affiche aussi le total d'heures loggées aujourd'hui (tous tickets confondus, que ça vienne de l'app ou directement du site Wrike), et peut proposer un lien direct vers ta feuille de temps.

## Prérequis

- Python 3.9+
- **Linux + GNOME** : le tray système nécessite le support AppIndicator/StatusNotifierItem. Sur **Ubuntu**, l'extension `ubuntu-appindicators` est présente mais **pas forcément activée** — vérifie avec :
  ```bash
  gnome-extensions info ubuntu-appindicators@ubuntu.com   # "Activé: Oui" / "État: ACTIVE" attendus
  ```
  Si besoin : `gnome-extensions enable ubuntu-appindicators@ubuntu.com`. ⚠️ Sous **Wayland**, une extension qu'on vient d'activer reste à l'état `INACTIVE` tant que la session GNOME Shell n'est pas relancée — il faut se **déconnecter/reconnecter** (ou redémarrer) pour qu'elle prenne effet, un simple `Alt+F2, r` ne fonctionne qu'en session X11.
  Sur un **autre GNOME** (Fedora, Debian vanilla, etc.) sans cette extension préinstallée :
  ```bash
  sudo apt install gnome-shell-extension-appindicator   # ou l'équivalent de ta distro
  ```
  puis active-la via l'app "Extensions" ou https://extensions.gnome.org (même contrainte de reconnexion sous Wayland).
- KDE, XFCE, Cinnamon, MATE : support natif, rien à installer.
- macOS / Windows : `pystray` bascule automatiquement sur le bon backend — non testé par ce projet (développé/vérifié sur Ubuntu GNOME) mais devrait fonctionner tel quel.
- **Terminal intégré VS Code (paquet snap)** : si tu lances l'app depuis ce terminal, `symbol lookup error: ... libpthread.so.0` peut apparaître — le snap injecte des variables GTK/GIO qui pointent vers ses propres bibliothèques, incompatibles avec le GTK système. `wrike_timer.py` neutralise automatiquement ces variables au lancement (uniquement celles qui pointent vers `/snap/`, donc sans effet dans un terminal normal) ; si le souci persiste, lance l'app depuis un terminal système classique.

## Installation

```bash
git clone <url-du-repo> wrike-timer
cd wrike-timer
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

⚠️ **Le `--system-site-packages` est obligatoire sur Linux.** Sans lui, `pystray` ne trouve pas les bindings GTK/AppIndicator du système, retombe sur un backend qui ne fonctionne pas sous GNOME, et l'app se lance sans erreur mais **aucune icône n'apparaît** dans le tray.

## Configuration du token

1. Sur Wrike : **Paramètres → Apps & Integrations → API → générer un Permanent Access Token** (usage perso, pas besoin d'app OAuth).
2. Puis :
   ```bash
   .venv/bin/python wrike_timer.py --set-token
   ```
   Le token est saisi de façon masquée et stocké dans le trousseau système (gnome-keyring ou équivalent). Si aucun trousseau n'est disponible sur la machine, il est stocké en fallback dans `~/.config/wrike-timer/config.json` (créé avec les permissions `600`).

   ⚠️ Cette commande a besoin d'un vrai terminal interactif. Si tu la lances depuis un contexte non-interactif (script, passthrough), la saisie masquée échoue avec `EOFError` — utilise plutôt `--set-token --token <valeur>` (le token apparaît alors en clair dans l'historique du shell, donc uniquement pour du scripting ponctuel).

**Ne partage et ne committe jamais ton token.** Chaque personne qui utilise ce repo génère le sien.

## Lancer l'app

```bash
.venv/bin/python wrike_timer.py
```

L'icône apparaît dans le tray. Le menu liste les 10 derniers tickets loggés ; un clic démarre le chrono, l'entrée "🔴 ..." en haut du menu permet de l'arrêter et pousse automatiquement le temps sur Wrike.

Si l'envoi échoue (réseau coupé, API indisponible), le temps tracké **n'est jamais perdu** : il reste dans une file d'attente locale (visible dans le menu, "⚠ N envoi(s) en attente") et est retenté automatiquement au prochain rafraîchissement, ou manuellement en cliquant sur l'entrée.

## Configuration (`~/.config/wrike-timer/config.json`)

| Clé | Défaut | Description |
|---|---|---|
| `refresh_interval_seconds` | `30` | Fréquence de rafraîchissement (liste des tickets, total du jour, retry des envois en attente) |
| `recent_tasks_limit` | `10` | Nombre de tickets affichés dans le menu |
| `recent_tasks_lookback_days` | `30` | Fenêtre (en jours) sur laquelle chercher les tickets récents |
| `timesheet_url` | `""` | URL de ta feuille de temps Wrike (copiée depuis la barre d'adresse du navigateur, sur ta page Timesheets). Si non vide, le menu affiche "📊 Ouvrir ma feuille de temps" (ouvre l'URL dans le navigateur par défaut). Si vide, le menu affiche "📊 Feuille de temps non configurée (clic = comment faire)", qui rappelle où ajouter cette clé. |

⚠️ Ne pas confondre avec `~/.local/share/wrike-timer/state.json` : ce second fichier est un **cache interne** (tickets récents, chrono actif, file de retry, heartbeat), entièrement réécrit par l'app à chaque cycle de rafraîchissement. Toute clé ajoutée à la main dedans est ignorée et finit par disparaître au prochain rafraîchissement — les réglages se mettent dans `config.json`, jamais dans `state.json`.

Le total "📅 Aujourd'hui : Xh XX" en haut du menu additionne les `hours` de tous tes timelogs `trackedDate` = aujourd'hui, peu importe s'ils ont été créés par cette app ou directement sur wrike.com. Il ne compte pas le temps du chrono en cours (pas encore loggé tant qu'il n'est pas arrêté).

## Lancement automatique au démarrage

```bash
.venv/bin/python wrike_timer.py --install-autostart    # active
.venv/bin/python wrike_timer.py --uninstall-autostart  # désactive
```

Sur Linux, ça écrit un fichier dans `~/.config/autostart/`. Pour macOS/Windows, pas d'automatisation fournie (non testé) :
- **macOS** : créer un LaunchAgent dans `~/Library/LaunchAgents/`.
- **Windows** : raccourci dans le dossier Démarrage, ou clé de registre.

## Développement

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Vérification périodique des CVE sur les dépendances :
```bash
.venv/bin/pip install pip-audit
.venv/bin/pip-audit
```

### CI (une fois poussé sur GitHub)

`.github/workflows/ci.yml` fait tourner `pytest` sur Python 3.11 et 3.12 à chaque push/PR, plus un job `pip-audit` (non bloquant — juste un signal). Les tests ne dépendent d'aucune bibliothèque GTK/AppIndicator (la logique qui touche pystray est réduite au minimum et le reste est testé en pur Python), donc pas de setup particulier côté runner.

`.github/dependabot.yml` ouvre automatiquement une PR chaque semaine si une dépendance (`requirements*.txt` ou les actions GitHub elles-mêmes) a une nouvelle version — la CI tourne dessus automatiquement, donc une mise à jour qui casse quelque chose se voit avant de merger. C'est la réponse à "comment on pense à mettre à jour" : Dependabot pense à ta place, tu n'as qu'à relire/merger les PR qu'il ouvre.

## Limitations connues

- **Pas de notion de "favoris".** L'API Wrike v4 n'expose ni champ, ni endpoint pour les tickets étoilés ("Starred tasks" est un smart folder purement côté UI Wrike, invisible depuis l'API) — impossible de les lire depuis cette app. La liste se limite aux tickets récents.
- Le tooltip (icône survolée) affichant le chrono en direct est best-effort : son rendu dépend de l'implémentation StatusNotifierItem du thème/DE utilisé.
- Le clic "démarrer/arrêter en un clic" se fait depuis le menu déroulant, pas par un clic direct sur l'icône : le protocole AppIndicator (GNOME/KDE) n'a pas de notion de clic gauche "action par défaut" distincte de l'ouverture du menu, contrairement à Windows.

## Sécurité

- `.gitignore` exclut `config.json`, `state.json` et les logs dès le premier commit — ne pas les forcer avec `git add -f`.
- Voir [AGENTS.md](AGENTS.md) pour les règles complètes sur les données sensibles à ne jamais partager.
