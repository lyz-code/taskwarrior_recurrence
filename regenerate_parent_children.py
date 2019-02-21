#!/usr/bin/python3
import sys
import tasklib
import taskwarrior_recurrence.main


def main():

    tw = tasklib.TaskWarrior(
        taskrc_location=sys.argv[1],
        data_location=sys.argv[2],
    )
    recurring_tasks = tw.tasks.filter(status='recurring')

    for task in recurring_tasks:
        try:
            child_task = tw.tasks.get(uuid=task['rlastinstance'])
        except Exception:
            import pdb; pdb.set_trace()  # XXX BREAKPOINT
        if child_task['status'] == 'deleted' or \
                child_task['status'] == 'completed':
            print('Regenerating child of {} - {}'.format(
                task['uuid'],
                task['description'],
            ))
            prt = taskwarrior_recurrence.main.ProcessRecurrentTask(child_task)
            task = prt.synthetize_next_child()


if __name__ == "__main__":
    main()
