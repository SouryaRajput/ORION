import subprocess
import platform

OS = platform.system()


def open_app(app_name: str):

    app_name = app_name.lower()

    try:

        if OS == "Darwin":  # macOS

            if "chrome" in app_name:
                subprocess.Popen(["open", "-a", "Google Chrome"])

            elif "safari" in app_name:
                subprocess.Popen(["open", "-a", "Safari"])

            elif "vscode" in app_name or "code" in app_name:
                subprocess.Popen(["open", "-a", "Visual Studio Code"])

            elif "terminal" in app_name:
                subprocess.Popen(["open", "-a", "Terminal"])

            elif "finder" in app_name:
                subprocess.Popen(["open", "-a", "Finder"])

            elif "spotify" in app_name:
                subprocess.Popen(["open", "-a", "Spotify"])

            elif "calculator" in app_name:
                subprocess.Popen(["open", "-a", "Calculator"])

            else:
                # Try to open dynamically if not specifically mapped
                try:
                    res = subprocess.run(["open", "-a", app_name.title()], capture_output=True)
                    if res.returncode != 0:
                        # Sometimes apps are not perfectly title-cased or the exact name
                        res = subprocess.run(["open", "-a", app_name], capture_output=True)
                        if res.returncode != 0:
                            return False
                except Exception:
                    return False

        elif OS == "Windows":

            subprocess.Popen(app_name)

        else:
            return False

        return True

    except Exception as e:
        print("[SYSTEM ERROR]", e)
        return False
    
def open_multiple(apps: list):

    results = []

    for app in apps:
        success = open_app(app)
        results.append((app, success))

    return results