from Core.logger import LogManager

def get_logger(name: str, level=None):
    return LogManager.get_logger(f"study.{name}", "system.log")
