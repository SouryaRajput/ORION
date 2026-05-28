from Core.system_control import open_app
from Core.app_registry import get_installed_apps, find_best_apps


def launch_workspace(intent: str):

    installed = get_installed_apps()

    selected_apps = find_best_apps(intent, installed)

    if not selected_apps:
        return "I couldn't find suitable apps"

    for app in selected_apps:
        open_app(app)

    return f"{intent} workspace ready"