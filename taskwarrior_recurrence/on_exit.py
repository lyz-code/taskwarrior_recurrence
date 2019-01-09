#!/usr/bin/python3
# #!/usr/bin/env python

import sys
import tasklib
try:
    from main import ProcessRecurrentTask
except ImportError:
    from .main import ProcessRecurrentTask


def main():

    # Create the Taskwarrior backend till
    # [this](https://github.com/robgolding/tasklib/issues/58) bug is fixed

    task_command = sys.argv[3].split(':')[1].strip()
    if (
        task_command != 'delete' and
        task_command != 'done' and
        True
    ):
        sys.exit(0)

    tw = tasklib.TaskWarrior(
        taskrc_location=sys.argv[4].split(':')[1],
        data_location=sys.argv[5].split(':')[1],
    )
    task = tasklib.task.Task.from_input(backend=tw)
    task_command = sys.argv[3].split(':')[1].strip()

    if task['r'] is None:
        sys.exit(0)

    prt = ProcessRecurrentTask(task)

    if task['rlastinstance'] is not None:
        if task_command == 'delete':
            prt.delete_child_task()
    else:
        prt.synthetize_next_child()

    sys.exit(0)


if __name__ == "__main__":
    main()
