#!/usr/bin/env python

import tzlocal
import tasklib
import datetime
from tasklib.task import Task
from tasklib.backends import TaskWarriorException


class ProcessRecurrentTask():
    '''Process an incoming recurrent task'''

    def __init__(self, task):
        self.task = task
        self.tw = task.backend
        self.local_zone = tzlocal.get_localzone()

    def add_recurrent_task(self):
        '''Creates a new chained task and it's child it works both
        for `rtype:chained` and `rtype:periodic`'''

        if self.task['r'] is None or self.task['due'] is None:
            print('You need to specify the r and due parameters')
            raise KeyError('You need to specify the r and due parameters')

        child_task = self._copy_task(pop=['rtype'])
        child_task['rparent'] = self.task['uuid']
        child_task.save()

        # Setup the recur type to r to hide the parent task under recurrence
        # tasks
        self.task['recur'] = self.task['r']
        self.task['rlastinstance'] = child_task['uuid']
        return self.task

    def delete_child_task(self):
        '''Deletes an existing child tasks'''
        child_task = self.tw.tasks.get(uuid=self.task['rlastinstance'])
        child_task.delete()

    def synthetize_next_child(self):
        '''Creates the next child task'''

        parent_task = self.tw.tasks.get(uuid=self.task['rparent'])

        if parent_task['rtype'] == 'chained':
            self.synthetize_next_chained()
        elif parent_task['rtype'] == 'periodic':
            self.synthetize_next_periodic()

    def synthetize_next_chained(self):
        '''Creates the next chained task and updates the parent task'''

        parent_task = self.tw.tasks.get(uuid=self.task['rparent'])

        if type(parent_task['rwait']) is str:
            parent_task['rwait'] = self.tw.convert_datetime_string(
                parent_task['rwait']
            )
        if type(parent_task['rscheduled']) is str:
            parent_task['rscheduled'] = self.tw.convert_datetime_string(
                parent_task['rscheduled']
            )

        if parent_task['status'] == 'deleted' or \
                parent_task['status'] == 'completed':
            return

        next_task = self._copy_task(
            pop=['due', 'recur', 'rlastinstance', 'status', 'end'],
            task=parent_task,
        )

        next_task['r'] = parent_task['r']
        next_task['rparent'] = parent_task['uuid']
        next_task['due'] = '{} + {}'.format(
            self.task['end'].isoformat(),
            next_task['r'],
        )
        if parent_task['rwait'] is not None:
            next_task['wait'] = '{} - ({} - {})'.format(
                    next_task['due'].isoformat(),
                    parent_task['due'].isoformat(),
                    parent_task['rwait'].isoformat(),
            )
        if parent_task['rscheduled'] is not None:
            next_task['scheduled'] = '{} - ({} - {})'.format(
                    next_task['due'].isoformat(),
                    parent_task['due'].isoformat(),
                    parent_task['rscheduled'].isoformat(),
            )

        try:
            next_task.save()
        except TaskWarriorException:
            # This ugly fix is needed because when the new task is created
            # as the data is not refreshed it tries to query an id that doesn't
            # exist so we have to query for the previous
            next_task._data['id'] -= 1
            next_task.refresh()

        parent_task['rlastinstance'] = next_task['uuid']

        parent_task.save()

    def synthetize_next_periodic(self):
        '''Creates the next periodic task and updates the parent task'''

        parent_task = self.tw.tasks.get(uuid=self.task['rparent'])
        if type(parent_task['rwait']) is str:
            parent_task['rwait'] = self.tw.convert_datetime_string(
                parent_task['rwait']
            )
        if type(parent_task['rscheduled']) is str:
            parent_task['rscheduled'] = self.tw.convert_datetime_string(
                parent_task['rscheduled']
            )
        if parent_task['status'] == 'deleted' or \
                parent_task['status'] == 'completed':
            return

        next_task_template = self._copy_task(
            pop=[
                'due',
                'recur',
                'rlastinstance',
                'rwait',
                'rscheduled',
                'status',
                'end',
            ],
            task=parent_task,
        )

        next_task_template['r'] = parent_task['r']
        next_task_template['rparent'] = parent_task['uuid']

        iteration = 1
        next_task = self._copy_task(
            pop=['due', 'recur', 'rlastinstance', 'status', 'end'],
            task=next_task_template
        )

        while True:
            next_task['due'] = '{} + {}*{}'.format(
                parent_task['due'].isoformat(),
                parent_task['r'],
                iteration,
            )
            if next_task['due'] > self.task['due']:
                try:
                    self.tw.tasks.get(
                        rparent=self.task['rparent'],
                        due=next_task['due'].isoformat(),
                    )
                except Task.DoesNotExist:
                    if parent_task['rwait'] is not None:
                        next_task['wait'] = '{} - ({} - {})'.format(
                                next_task['due'].isoformat(),
                                parent_task['due'].isoformat(),
                                parent_task['rwait'].isoformat(),
                        )
                    if parent_task['rscheduled'] is not None:
                        next_task['scheduled'] = '{} - ({} - {})'.format(
                                next_task['due'].isoformat(),
                                parent_task['due'].isoformat(),
                                parent_task['rscheduled'].isoformat(),
                        )
                    next_task.save()
                if next_task['due'] > self.local_zone.localize(
                    datetime.datetime.now()
                ):
                    break
                next_task = self._copy_task(task=next_task_template)

            iteration += 1

        # try:
        # next_task.save()
        # except TaskWarriorException:
        #     # This ugly fix is needed because when the new task is created
        #    # as the data is not refreshed it tries to query an id that doesn't
        #     # exist so we have to query for the previous
        #     next_task._data['id'] -= 1
        #     next_task.refresh()

        parent_task['rlastinstance'] = next_task['uuid']
        parent_task.save()

    def _copy_task(self, pop=[], task=None):
        '''Copies the self.task stripping unneeded information and returns the
        task object.

        It accepts in pop a list of items to pop'''

        if task is None:
            new_task_data = self.task._data.copy()
        else:
            new_task_data = task._data.copy()
        pop.append('entry')
        pop.append('modified')
        pop.append('mask')
        pop.append('uuid')
        pop.append('id')
        pop.append('urgency')
        pop.append('status')

        for item in pop:
            try:
                new_task_data[item]
                new_task_data.pop(item)
            except KeyError:
                pass

        new_task = tasklib.Task(self.tw)
        for key, value in new_task_data.items():
            new_task[key] = value
        return new_task
