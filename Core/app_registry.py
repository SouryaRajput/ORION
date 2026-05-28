import os

APP_DIRS = [
    "/Applications",
    "/System/Applications",
    "/System/Applications/Utilities"
]


def get_installed_apps():

    apps = []

    for app_dir in APP_DIRS:
        try:
            if not os.path.exists(app_dir):
                continue
                
            for item in os.listdir(app_dir):

                if item.endswith(".app"):
                    name = item.replace(".app", "").lower()
                    apps.append(name)

        except Exception as e:
            print(f"[APP SCAN ERROR] {app_dir}:", e)

    return list(set(apps))

def find_best_apps(intent, installed_apps):

    intent = intent.lower()

    selected = []

    for app in installed_apps:

        if intent == "study":

            if any(k in app for k in ["chrome", "safari", "edge"]):
                selected.append(app)

            elif any(k in app for k in ["code", "vscode"]):
                selected.append(app)

            elif "notion" in app or "notes" in app:
                selected.append(app)

        elif intent == "coding":

            if any(k in app for k in ["code", "vscode"]):
                selected.append(app)

            elif "terminal" in app:
                selected.append(app)

            elif any(k in app for k in ["chrome", "safari"]):
                selected.append(app)

        elif intent == "entertainment":

            if "spotify" in app:
                selected.append(app)

            elif any(k in app for k in ["chrome", "safari"]):
                selected.append(app)

    return list(set(selected))