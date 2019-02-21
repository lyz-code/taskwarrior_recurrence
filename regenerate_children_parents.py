#!/usr/bin/python3
import sys
import tasklib


def main():

    tw = tasklib.TaskWarrior(
        taskrc_location=sys.argv[1],
        data_location=sys.argv[2],
    )
    children_recurring_tasks = tw.tasks.filter(rparent__not=None)

    for task in children_recurring_tasks:
        if task['status'] in ['completed', 'deleted', 'recurring']:
            continue
        parent_task = tw.tasks.get(uuid=task['rparent'])
        if parent_task['rlastinstance'] != task['uuid']:
            print('Regenerating rlastinstance of {} - {}'.format(
                parent_task['uuid'],
                parent_task['description'],
            ))
            parent_task['rlastinstance'] = task['uuid']
            parent_task.save()


if __name__ == "__main__":
    main()
