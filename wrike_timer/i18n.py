"""Minimal string catalog for the tray UI, selected via config's "language" key.

Not a general-purpose i18n framework — just enough to keep the handful of
tray/notification strings translatable without duplicating _build_menu logic
per language. Defaults to "en"; set "language": "fr" in config.json to get
the app's original French strings back.
"""

_current_lang = "en"

_STRINGS = {
    "today_total": {
        "fr": "📅 Aujourd'hui : {hours}",
        "en": "📅 Today: {hours}",
    },
    "resume_gap": {
        "fr": "⚠️ Reprise après ~{gap} d'interruption détectée",
        "en": "⚠️ Resumed after a ~{gap} gap (interruption detected)",
    },
    "no_recent_tasks": {
        "fr": "(aucun ticket récent — Rafraîchir)",
        "en": "(no recent tasks — Refresh)",
    },
    "pending_timelogs": {
        "fr": "⚠ {count} envoi(s) en attente",
        "en": "⚠ {count} pending submission(s)",
    },
    "refresh_list": {
        "fr": "🔄 Rafraîchir la liste",
        "en": "🔄 Refresh list",
    },
    "open_timesheet": {
        "fr": "📊 Ouvrir ma feuille de temps",
        "en": "📊 Open my timesheet",
    },
    "timesheet_not_configured": {
        "fr": "📊 Feuille de temps non configurée (clic = comment faire)",
        "en": "📊 Timesheet not configured (click for instructions)",
    },
    "settings": {
        "fr": "⚙️ Paramètres",
        "en": "⚙️ Settings",
    },
    "quit": {
        "fr": "Quitter",
        "en": "Quit",
    },
    "settings_notification_title": {
        "fr": "Wrike Timer — Paramètres",
        "en": "Wrike Timer — Settings",
    },
    "timesheet_missing_notification_title": {
        "fr": "Wrike Timer — Feuille de temps",
        "en": "Wrike Timer — Timesheet",
    },
    "timesheet_missing_notification_body": {
        "fr": (
            'Ajoute "timesheet_url": "<ton url>" dans {config_path}\n'
            "(copie l'URL depuis ton navigateur, sur ta page Timesheets Wrike)."
        ),
        "en": (
            'Add "timesheet_url": "<your url>" to {config_path}\n'
            "(copy the URL from your browser, on your Wrike Timesheets page)."
        ),
    },
    "unconfigured_menu_item": {
        "fr": "⚠ Configuration requise — lancer : wrike_timer.py --set-token",
        "en": "⚠ Configuration required — run: wrike_timer.py --set-token",
    },
    "unconfigured_icon_title": {
        "fr": "Wrike Timer — non configuré",
        "en": "Wrike Timer — not configured",
    },
}


def set_language(lang):
    global _current_lang
    _current_lang = lang if lang in ("fr", "en") else "en"


def t(key, **kwargs):
    template = _STRINGS[key][_current_lang]
    return template.format(**kwargs) if kwargs else template
