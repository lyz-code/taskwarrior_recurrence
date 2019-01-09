import unittest
import datetime
from unittest.mock import patch
from taskwarrior_recurrence.on_exit import main


class TestOnExit(unittest.TestCase):
    def setUp(self):
        self.print_patch = patch('taskwarrior_recurrence.on_exit.print')
        self.print = self.print_patch.start()
        self.tasklib_patch = patch('taskwarrior_recurrence.on_exit.tasklib')
        self.tasklib = self.tasklib_patch.start()
        self.task = self.tasklib.task.Task.from_input.return_value
        self.sys_patch = patch('taskwarrior_recurrence.on_exit.sys')
        self.sys = self.sys_patch.start()
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: ',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        self.prt_patch = patch(
            'taskwarrior_recurrence.on_exit.ProcessRecurrentTask'
        )
        self.prt = self.prt_patch.start()
        self.prt = self.prt.return_value

    def tearDown(self):
        self.tasklib_patch.stop()
        self.sys_patch.stop()
        self.print_patch.stop()
        self.prt_patch.stop()

    def test_task_backend_is_configured(self):
        main()
        self.assertEqual(
            self.tasklib.TaskWarrior.assert_called_with(
                taskrc_location='/path/to/rc_file',
                data_location='/path/to/data',
            ),
            None
        )

    def test_main_loads_data(self):
        main()
        self.assertTrue(self.tasklib.task.Task.from_input.called)

    def test_main_doesnt_output_anything_on_exit(self):
        main()
        self.assertFalse(self.print.called)

    def test_if_task_doesnt_have_r_uda_do_nothing(self):
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "r": None,
            "rlastinstance": None,
            "description": "This is a task without rtype",
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()

        # If I use sys.exit(0) mock as sys.exit it exits all the tests,
        # therefore I can't use self.assertFalse(processrecurMock.called)
        # So instead I make sure that the sys.exit(0) is called twice
        self.assertEqual(len(self.sys.mock_calls), 3)

    def test_if_chained_task_deleted_create_next_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: delete',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "deleted",
            "r": '3d',
            "rlastinstance": None,
            "rparent": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a chained task",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.synthetize_next_child.called)

    def test_if_chained_task_completed_create_next_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: done',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "completed",
            "r": '3d',
            "rlastinstance": None,
            "rparent": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a chained task",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.synthetize_next_child.called)

    def test_if_parent_task_deleted_delete_chained_child_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: delete',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "deleted",
            "r": '3d',
            "rlastinstance": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a chained task",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.delete_child_task.called)

    def test_if_periodic_task_deleted_create_next_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: delete',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "deleted",
            "r": '3d',
            "rlastinstance": None,
            "rparent": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a task without rtype",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.synthetize_next_child.called)

    def test_if_periodic_task_completed_create_next_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: done',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "completed",
            "r": '3d',
            "rlastinstance": None,
            "rparent": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a periodic task",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.synthetize_next_child.called)

    def test_if_parent_task_deleted_delete_periodic_child_task(self):
        self.sys.argv = [
              '/path/to/hook/script',
              'api:2',
              'args:/path/to/rc_file',
              'command: delete',
              'rc:/path/to/rc_file',
              'data:/path/to/data',
              'version:2.5.1',
        ]
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "deleted",
            "r": '3d',
            "rlastinstance": "88781555-f66c-40b1-9c17-11d81d6e7864",
            "description": "This is a task without rtype",
            "end": datetime.datetime.strptime(
                '20180809T085429',
                "%Y%m%dT%H%M%S",
            ),
            "due": datetime.datetime.strptime(
                '20180808T010000',
                "%Y%m%dT%H%M%S",
            ),
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(self.prt.delete_child_task.called)
