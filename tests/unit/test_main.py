import os
import json
import tasklib
import tzlocal
import datetime
import unittest
import tempfile
import shutil
from tasklib.task import Task
from unittest.mock import patch, call

from taskwarrior_recurrence.main import ProcessRecurrentTask


class TestProcessRecurrentTask(unittest.TestCase):
    def setUp(self):
        self.print_patch = patch('taskwarrior_recurrence.main.print')
        self.print = self.print_patch.start()
        self.tasklib_patch = patch('taskwarrior_recurrence.main.tasklib')
        self.tasklib = self.tasklib_patch.start()
        self.task = self.tasklib.task.Task.from_input.return_value

        self.task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "description": "This is a chained recurring task",
            "rtype": "chained",
            "due": '20180808T085429Z',
            "r": '3d',
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.task.__getitem__.side_effect = self.task_data.__getitem__
        self.task.__setitem__.side_effect = self.task_data.__setitem__
        self.task._data.copy.return_value = dict(self.task_data)
        self.prt = ProcessRecurrentTask(self.task)

    def tearDown(self):
        self.tasklib_patch.stop()
        self.print_patch.stop()

    def test_task_attribute_is_created(self):
        self.assertEqual(self.prt.task, self.task)

    def test_tw_attribute_is_created(self):
        self.assertEqual(self.prt.tw, self.task.backend)

    def test_add_chained_fails_if_task_doesnt_have_due(self):
        self.task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "description": "This is a chained recurring task",
            "rtype": "chained",
            "due": None,
            "r": "3d",
            "project": 'test_project'
        }
        self.task.__getitem__.side_effect = self.task_data.__getitem__
        self.prt = ProcessRecurrentTask(self.task)

        with self.assertRaises(KeyError):
            self.prt.add_recurrent_task()

        self.assertEqual(
            self.print.assert_called_with(
                'You need to specify the r and due parameters'
            ),
            None
        )

    def test_add_chained_fails_if_task_doesnt_have_recur(self):
        self.task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "description": "This is a chained recurring task",
            "rtype": "chained",
            "due": '20180808T085429Z',
            "project": 'test_project'
        }
        self.task.__getitem__.side_effect = self.task_data.__getitem__
        self.prt = ProcessRecurrentTask(self.task)
        with self.assertRaises(KeyError):
            self.prt.add_recurrent_task()

    @patch('taskwarrior_recurrence.main.ProcessRecurrentTask._copy_task')
    def test_add_chained_creates_child_task(self, copyMock):
        self.prt.add_recurrent_task()
        self.assertEqual(
            copyMock.mock_calls[0],
            call(pop=['rtype']),
        )
        self.assertEqual(
            copyMock.return_value.__setitem__.mock_calls,
            [call('rparent', self.task['uuid'])]
        )
        self.assertTrue(copyMock.return_value.save.called)

    def test_add_recurrent_sets_recur_to_r_in_parent(self):
        parent_task = self.prt.add_recurrent_task()
        self.assertEqual(parent_task['recur'], parent_task['r'])

    def test_add_recurrent_sets_rlastinstance_to_child_uuid_in_parent(self):
        parent_task = self.prt.add_recurrent_task()
        child_task = self.tasklib.Task.return_value
        self.assertEqual(parent_task['rlastinstance'], child_task['uuid'])

    def test_copy_task_strips_necessary_data(self):
        returned_task = self.prt._copy_task(pop=[])
        self.assertEqual(
            self.tasklib.Task.assert_called_with(
                self.task.backend
            ),
            None,
        )
        new_task = self.tasklib.Task.return_value
        self.assertTrue(
            call('description', self.task['description'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(
            call('myuda', self.task['myuda'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(
            call('project', self.task['project'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(
            call('r', self.task['r'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(
            call('rtype', self.task['rtype'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(
            call('due', self.task['due'])
            in new_task.__setitem__.mock_calls
        )
        self.assertTrue(len(new_task.__setitem__.mock_calls) == 6)
        self.assertTrue(returned_task == self.tasklib.Task.return_value)

    def test_copy_task_can_accept_pop_list(self):
        self.prt._copy_task(pop=['description'])
        new_task = self.tasklib.Task.return_value
        self.assertFalse(
            call('description', self.task['description'])
            in new_task.__setitem__.mock_calls
        )

    def test_copy_task_can_accept_task_object(self):
        other_task = self.task
        self.prt._copy_task(task=other_task)
        new_task = self.tasklib.Task.return_value
        self.assertTrue(
            call('description', self.task['description'])
            in new_task.__setitem__.mock_calls
        )

    def test_copy_task_doesnt_fail_if_element_doesnt_exist(self):
        self.prt._copy_task(pop=['unexistent_field'])


class TestChildChainedTask(unittest.TestCase):

    def setUp(self):
        self.print_patch = patch('taskwarrior_recurrence.main.print')
        self.print = self.print_patch.start()
        self.tasklib_patch = patch('taskwarrior_recurrence.main.tasklib')
        self.tasklib = self.tasklib_patch.start()
        self.copy_task_patch = patch(
            'taskwarrior_recurrence.main.ProcessRecurrentTask._copy_task'
        )
        self.copy_task = self.copy_task_patch.start()

        self.input_patch = patch('taskwarrior_recurrence.main.input')
        self.input = self.input_patch.start()

        self.task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "description": "This is a chained recurring task",
            "end": datetime.datetime.strptime(
                '20180808T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
            "r": '3d',
            "rparent": "012339c8-a8fe-41da-82db-a990f989237e",
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.task = self.tasklib.task.Task.from_input.return_value
        self.task.__getitem__.side_effect = self.task_data.__getitem__
        self.task.__setitem__.side_effect = self.task_data.__setitem__
        self.task._data.copy.return_value = dict(self.task_data)
        self.parent_task_data = {
            "entry": "20180701T194712Z",
            "uuid": "3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "modified": "20180706T085429Z",
            "status": "recurring",
            "description": "This is a chained recurring task",
            "due": datetime.datetime.strptime(
                '20180708T010000',
                "%Y%m%dT%H%M%S",
            ),
            "rwait": None,
            "rscheduled": None,
            "r": '3d',
            'rtype': 'chained',
            "recur": '3d',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.task.backend.tasks.get.return_value
        self.parent_task.__getitem__.side_effect = \
            self.parent_task_data.__getitem__
        self.parent_task.__setitem__.side_effect = \
            self.parent_task_data.__setitem__
        self.parent_task._data.copy.return_value = self.parent_task_data.copy()
        self.prt = ProcessRecurrentTask(self.task)

    def tearDown(self):
        self.input_patch.stop()
        self.tasklib_patch.stop()
        self.copy_task_patch.stop()
        self.print_patch.stop()

    def test_delete_recurrent_task_deletes_child(self):
        self.task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "description": "This is a chained recurring task",
            "rtype": "chained",
            "rlastinstance": "012339c8-a8fe-41da-82db-a990f989237e",
            "due": '20180808T085429Z',
            "rwait": '20180802T085429Z',
            "r": '3d',
        }
        self.task.__getitem__.side_effect = self.task_data.__getitem__
        self.task._data.copy.return_value = self.task_data.copy()
        self.prt = ProcessRecurrentTask(self.task)
        self.prt.delete_child_task()
        self.assertTrue(self.task.backend.tasks.get.called)
        self.assertTrue(self.task.backend.tasks.get.return_value.delete.called)

    def test_synthetize_next_chained_creates_new_clean_task(self):
        self.prt.synthetize_next_chained()

        self.assertEqual(
            self.copy_task.mock_calls[0],
            call(pop=[
                'due',
                'recur',
                'rlastinstance',
                'status',
                'end'
            ], task=self.parent_task
            ),
        )
        self.assertTrue(self.copy_task.return_value.save.called)

    def test_synthetize_next_chained_doesnt_create_task_if_parent_dead(self):
        self.parent_task_data = {
            "entry": "20180701T194712Z",
            "uuid": "3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "modified": "20180706T085429Z",
            "status": "deleted",
            "description": "This is a chained recurring task",
            "due": datetime.datetime.strptime(
                '20180708T010000',
                "%Y%m%dT%H%M%S",
            ),
            "rwait": None,
            "rscheduled": None,
            "r": '3d',
            "recur": '3d',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.task.backend.tasks.get.return_value
        self.parent_task.__getitem__.side_effect = \
            self.parent_task_data.__getitem__
        self.parent_task.__setitem__.side_effect = \
            self.parent_task_data.__setitem__
        self.parent_task._data.copy.return_value = self.parent_task_data.copy()
        self.prt.synthetize_next_chained()

        self.assertFalse(self.copy_task.return_value.save.called)

    def test_synthetize_next_chained_doesnt_create_task_if_parent_done(self):
        self.parent_task_data = {
            "entry": "20180701T194712Z",
            "uuid": "3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "modified": "20180706T085429Z",
            "status": "completed",
            "description": "This is a chained recurring task",
            "due": datetime.datetime.strptime(
                '20180708T010000',
                "%Y%m%dT%H%M%S",
            ),
            "rwait": None,
            "rscheduled": None,
            "r": '3d',
            "recur": '3d',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.task.backend.tasks.get.return_value
        self.parent_task.__getitem__.side_effect = \
            self.parent_task_data.__getitem__
        self.parent_task.__setitem__.side_effect = \
            self.parent_task_data.__setitem__
        self.parent_task._data.copy.return_value = self.parent_task_data.copy()
        self.prt.synthetize_next_chained()

        self.assertFalse(self.copy_task.return_value.save.called)

    def test_synthetize_next_chained_sets_rparent_on_child(self):
        self.prt.synthetize_next_chained()

        self.assertTrue(
            call('rparent', '3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa') in
            self.copy_task.return_value.__setitem__.mock_calls,
        )

    def test_synthetize_next_chained_shifts_due(self):
        self.copy_task.return_value.__getitem__.return_value = '3d'
        self.prt.synthetize_next_chained()

        self.assertTrue(
            call('due', '2018-08-08T08:54:29 + 3d') in
            self.copy_task.return_value.__setitem__.mock_calls,
        )

    def test_synthetize_next_chained_shifts_wait(self):
        self.parent_task_data['rwait'] = datetime.datetime.strptime(
            '20180706T010000',
            "%Y%m%dT%H%M%S",
        )
        next_task_due = datetime.datetime.strptime(
            '20180816T010000',
            "%Y%m%dT%H%M%S",
        )
        next_task = self.copy_task.return_value
        next_task.__getitem__.return_value = next_task_due

        self.prt.synthetize_next_chained()

        # instance.wait: new_instance.due - (template.due - template.wait)
        self.assertTrue(
            call(
                'wait', '{} - ({} - {})'.format(
                    next_task_due.isoformat(),
                    self.parent_task_data['due'].isoformat(),
                    self.parent_task_data['rwait'].isoformat()
                )
            ) in
            next_task.__setitem__.mock_calls
        )

    def test_synthetize_next_chained_shifts_scheduled(self):
        self.parent_task_data['rscheduled'] = datetime.datetime.strptime(
                '20180706T010000',
                "%Y%m%dT%H%M%S",
            )
        next_task_due = datetime.datetime.strptime(
            '20180816T010000',
            "%Y%m%dT%H%M%S",
        )
        next_task = self.copy_task.return_value
        next_task.__getitem__.return_value = next_task_due

        self.prt.synthetize_next_chained()

        # instance.scheduled: new_instance.due - \
        # (template.due - template.scheduled)
        self.assertTrue(
            call(
                'scheduled', '{} - ({} - {})'.format(
                    next_task_due.isoformat(),
                    self.parent_task_data['due'].isoformat(),
                    self.parent_task_data['rscheduled'].isoformat()
                )
            ) in
            next_task.__setitem__.mock_calls
        )

    def test_synthetize_next_chained_doesnt_wait_or_schedule_if_not_set(self):
        next_task = self.copy_task.return_value
        self.prt.synthetize_next_chained()
        # By default it only set's the due, rparent and r
        self.assertEqual(len(next_task.__setitem__.mock_calls), 3)

    def test_synthetize_next_chained_updates_parent_last(self):
        self.copy_task.return_value.__getitem__.side_effect = \
            self.task_data.__getitem__

        self.prt.synthetize_next_chained()
        parent_task = self.task.backend.tasks.get.return_value
        self.assertEqual(
            self.task.backend.tasks.get.mock_calls[0],
            call(uuid='012339c8-a8fe-41da-82db-a990f989237e'),
        )
        self.assertEqual(
            parent_task.__setitem__.mock_calls,
            [call('rlastinstance', "3f0a43d0-a713-4ebe-9e5c-b1facf49f078")]
        )
        self.assertTrue(parent_task.save.called)

    @patch(
        'taskwarrior_recurrence.main.ProcessRecurrentTask.'
        'synthetize_next_chained'
    )
    def test_synthetize_next_child_on_chained_calls_chained_method(
        self,
        chainedMock,
    ):
        self.prt.synthetize_next_child()
        self.assertTrue(chainedMock.called)


class TestChildPeriodicTask(unittest.TestCase):

    def setUp(self):
        self.local_zone = tzlocal.get_localzone()

        self.tzlocal_patch = patch('taskwarrior_recurrence.main.tzlocal')
        self.tzlocal = self.tzlocal_patch.start()

        self.temp_dir = tempfile.mkdtemp()
        shutil.copyfile('tests/files/taskrc', self.temp_dir + '/taskrc')

        self.tw = tasklib.TaskWarrior(
            taskrc_location=self.temp_dir + '/taskrc',
            data_location=self.temp_dir,
        )

        self.task_data = {
            "entry": "20370702T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20370708T085429Z",
            "status": "completed",
            "description": "This is a periodic recurring task",
            "end": '20370708T085429',
            "due": '20370708T010000',
            "r": '1w',
            "rparent": "012339c8-a8fe-41da-82db-a990f989237e",
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.task = self.import_task(self.task_data)

        self.parent_task_data = {
            "entry": "20370701T194712Z",
            "uuid": "012339c8-a8fe-41da-82db-a990f989237e",
            "modified": "20370706T085429Z",
            "status": "recurring",
            "description": "This is a periodic recurring task",
            "due": '20370708T010000',
            "r": '1w',
            'rtype': 'periodic',
            "recur": '1w',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.import_task(self.parent_task_data)

        self.tzlocal.get_localzone.return_value.localize.return_value = \
            self.local_zone.localize(
                datetime.datetime.strptime(
                    self.task_data['end'],
                    '%Y%m%dT%H%M%S'
                )
            )

        self.prt = ProcessRecurrentTask(self.task)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.tzlocal_patch.stop()

    def import_task(self, task_data):
        json_path = os.path.join(self.temp_dir, 'task_data.json')
        with open(json_path, 'w') as f:
            f.write(json.dumps(task_data))
        self.tw.execute_command(['import', json_path])
        return self.tw.tasks.get(uuid=task_data['uuid'])

    def test_synthetize_next_periodic_creates_new_clean_task(self):
        # Make sure there isn't any created task
        with self.assertRaises(Task.DoesNotExist):
            self.tw.tasks.get(
                rparent=self.parent_task_data['uuid'],
                status='pending'
            )

        self.prt.synthetize_next_periodic()

        tasks = self.tw.tasks.filter(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )
        self.assertEqual(len(tasks), 1)

    def test_synthetize_next_periodic_doesnt_create_task_if_parent_dead(self):
        self.parent_task_data = {
            "entry": "20370701T194712Z",
            "uuid": "3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "modified": "20370706T085429Z",
            "status": "deleted",
            "description": "This is a chained recurring task",
            "due": '20370708T010000',
            "r": '3d',
            'rtype': 'periodic',
            "recur": '3d',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.import_task(self.parent_task_data)

        self.prt.synthetize_next_periodic()

        with self.assertRaises(Task.DoesNotExist):
            self.tw.tasks.get(
                rparent=self.parent_task_data['uuid'],
                status='pending'
            )

    def test_synthetize_next_periodic_doesnt_create_task_if_parent_done(self):
        self.parent_task_data = {
            "entry": "20370701T194712Z",
            "uuid": "3f0aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "modified": "20370706T085429Z",
            "status": "completed",
            "description": "This is a chained recurring task",
            "due": '20370708T010000',
            "r": '3d',
            'rtype': 'periodic',
            "recur": '3d',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.import_task(self.parent_task_data)

        self.prt.synthetize_next_periodic()

        with self.assertRaises(Task.DoesNotExist):
            self.tw.tasks.get(
                rparent=self.parent_task_data['uuid'],
                status='pending'
            )

    def test_synthetize_next_periodic_sets_rparent_on_child(self):
        self.prt.synthetize_next_periodic()

        task = self.tw.tasks.get(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )
        self.assertEqual(
            task['rparent'],
            "012339c8-a8fe-41da-82db-a990f989237e",
        )

    def test_synthetize_next_periodic_shifts_due(self):
        '''In this test we will assume that the current date is the same as the
        completion of the last periodic child'''
        self.prt.synthetize_next_periodic()

        tasks = self.tw.tasks.filter(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )
        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            tasks[0]['due'].isoformat(),
            '2037-07-15T01:00:00+02:00',
        )

    def test_synthetize_tasks_till_next_one_from_now(self):
        '''In this test we will assume that the current date is the completion
        of a child task, but there should be 3 new tasks'''
        self.tzlocal.get_localzone.return_value.localize.return_value = \
            self.local_zone.localize(
                datetime.datetime.strptime(
                    '20370723T085429',
                    '%Y%m%dT%H%M%S',
                )
            )
        self.prt = ProcessRecurrentTask(self.task)
        self.prt.synthetize_next_periodic()

        tasks = self.tw.tasks.filter(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )
        self.assertEqual(len(tasks), 3)
        self.assertEqual(
            tasks[2]['due'].isoformat(),
            '2037-07-29T01:00:00+02:00',
        )

    def test_synthetize_doesnt_duplicate_tasks_if_they_exist(self):
        '''If the method is idempotent it should only create one task'''

        self.prt.synthetize_next_periodic()
        self.prt.synthetize_next_periodic()

        tasks = self.tw.tasks.filter(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )
        self.assertEqual(len(tasks), 1)

    def test_synthetize_next_periodic_shifts_wait(self):

        self.parent_task.delete()
        self.parent_task_data = {
            "entry": "20370701T194712Z",
            "uuid": "012339c8-a8fe-41da-82db-a990f989237e",
            "modified": "20370706T085429Z",
            "status": "recurring",
            "description": "This is a waiting periodic recurring task",
            "due": '20370708T010000',
            "rwait": '20370705T010000',
            "r": '1w',
            'rtype': 'periodic',
            "recur": '1w',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.import_task(self.parent_task_data)

        self.prt.synthetize_next_periodic()

        task = self.tw.tasks.get(
            rparent=self.parent_task_data['uuid'],
            status='waiting'
        )

        self.assertEqual(
            task['wait'].isoformat(),
            '2037-07-12T01:00:00+02:00',
        )

    def test_synthetize_next_periodic_shifts_scheduled(self):

        self.parent_task_data = {
            "entry": "20370701T194712Z",
            "uuid": "012339c8-a8fe-41da-82db-a990f989237e",
            "modified": "20370706T085429Z",
            "status": "recurring",
            "description": "This is a periodic recurring task",
            "due": '20370708T010000',
            "rscheduled": '20370705T010000',
            "r": '1w',
            'rtype': 'periodic',
            "recur": '1w',
            "rlastinstance": self.task_data['uuid'],
            "project": 'test_project',
            "myuda": 'udavalue',
        }
        self.parent_task = self.import_task(self.parent_task_data)

        self.prt.synthetize_next_periodic()

        task = self.tw.tasks.get(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )

        self.assertEqual(
            task['scheduled'].isoformat(),
            '2037-07-12T01:00:00+02:00',
        )

    def test_synthetize_next_periodic_doesnt_wait_or_schedule_if_not_set(self):

        self.prt.synthetize_next_periodic()

        task = self.tw.tasks.get(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )

        self.assertEqual(
            task['scheduled'],
            None,
        )
        self.assertEqual(
            task['wait'],
            None,
        )

    def test_synthetize_next_periodic_updates_parent_last(self):

        self.prt.synthetize_next_periodic()

        parent_task = self.tw.tasks.get(uuid=self.parent_task_data['uuid'])
        task = self.tw.tasks.get(
            rparent=self.parent_task_data['uuid'],
            status='pending'
        )

        self.assertEqual(
            parent_task['rlastinstance'],
            task['uuid'],
        )

    @patch(
        'taskwarrior_recurrence.main.ProcessRecurrentTask.'
        'synthetize_next_periodic'
    )
    def test_synthetize_next_child_on_periodic_calls_periodic_method(
        self,
        periodicMock,
    ):
        self.prt.synthetize_next_child()
        self.assertTrue(periodicMock.called)
