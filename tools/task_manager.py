current_task = None


def start_task(goal, steps):

    global current_task

    current_task = {
        "goal": goal,
        "steps": steps,
        "current_step": 0
    }


def get_current_task():
    return current_task


def advance_step():

    global current_task

    if not current_task:
        return None

    current_task["current_step"] += 1

    if current_task["current_step"] >= len(current_task["steps"]):
        finished_task = current_task
        current_task = None
        return finished_task

    return current_task


def reset_task():

    global current_task
    current_task = None