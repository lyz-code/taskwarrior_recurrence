#!/usr/bin/python3

import sys
import tasklib

# I need this to import for the tests and for the final file
try:
    from main import ProcessRecurrentTask
except ImportError:
    from .main import ProcessRecurrentTask


def main():

    # Create the Taskwarrior backend till
    # [this](https://github.com/robgolding/tasklib/issues/58) bug is fixed

    tw = tasklib.TaskWarrior(
        taskrc_location=sys.argv[4].split(':')[1],
        data_location=sys.argv[5].split(':')[1],
    )
    task = tasklib.task.Task.from_input(backend=tw)

    if task['r'] is None or task['rparent'] is not None:
        print(task.export_data())
        sys.exit(0)

    prt = ProcessRecurrentTask(task)

    if task['rtype'] == 'chained' or task['rtype'] == 'periodic':
        task = prt.add_recurrent_task()

    print(task.export_data())
    sys.exit(0)


if __name__ == "__main__":
    main()
