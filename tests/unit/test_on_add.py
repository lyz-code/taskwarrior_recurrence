import unittest
from unittest.mock import patch

from taskwarrior_recurrence.on_add import main


class TestOnAdd(unittest.TestCase):
    def setUp(self):
        self.print_patch = patch('taskwarrior_recurrence.on_add.print')
        self.print = self.print_patch.start()
        self.tasklib_patch = patch('taskwarrior_recurrence.on_add.tasklib')
        self.tasklib = self.tasklib_patch.start()
        self.task = self.tasklib.task.Task.from_input.return_value
        self.sys_patch = patch('taskwarrior_recurrence.on_add.sys')
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

    def tearDown(self):
        self.tasklib_patch.stop()
        self.sys_patch.stop()
        self.print_patch.stop()

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

    def test_main_outputs_a_the_result_on_exit(self):
        main()
        self.assertEqual(
            self.print.assert_called_with(
                self.task.export_data.return_value
            ),
            None,
        )

    def test_if_task_doesnt_have_r_uda_do_nothing(self):
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "rtype": None,
            "r": None,
            "description": "This is a task without rtype",
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertEqual(
            self.print.assert_called_with(
                self.task.export_data.return_value
            ),
            None,
        )

        # If I use sys.exit(0) mock as sys.exit it exits all the tests,
        # therefore I can't use self.assertFalse(processrecurMock.called)
        # So instead I make sure that the sys.exit(0) is called twice
        self.assertEqual(len(self.sys.mock_calls), 2)

    @patch('taskwarrior_recurrence.on_add.ProcessRecurrentTask')
    def test_if_task_has_rtype_chained_calls_add_recurrent(self, processMock):
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "status": "pending",
            "rtype": 'chained',
            "r": '2d',
            "rparent": None,
            "description": "This is a task without rtype",
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(processMock.return_value.add_recurrent_task.called)

    @patch('taskwarrior_recurrence.on_add.ProcessRecurrentTask')
    def test_if_task_has_rtype_periodic_calls_add_recurrent(self, processMock):
        task_data = {
            'entry': '20180802T194712Z',
            'uuid': '3f0a43d0-a713-4ebe-9e5c-b1facf49f078',
            'modified': '20180806T085429Z',
            'status': 'pending',
            'rtype': 'periodic',
            'r': '2d',
            'rparent': None,
            'description': "This is a task without rtype",
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertTrue(processMock.return_value.add_recurrent_task.called)
    def test_if_task_has_rparent_uda_do_nothing(self):
        task_data = {
            "entry": "20180802T194712Z",
            "uuid": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "modified": "20180806T085429Z",
            "rparent": "3f0a43d0-a713-4ebe-9e5c-b1facf49f078",
            "status": "pending",
            "rtype": 'chained',
            "r": '2d',
            "due": "monday",
            "description": "This is a task without rtype",
        }
        self.task.__getitem__.side_effect = task_data.__getitem__
        self.task.__setitem__.side_effect = task_data.__setitem__
        self.task._data.copy.return_value = task_data.copy()
        main()
        self.assertEqual(
            self.print.assert_called_with(
                self.task.export_data.return_value
            ),
            None,
        )

        # If I use sys.exit(0) mock as sys.exit it exits all the tests,
        # therefore I can't use self.assertFalse(processrecurMock.called)
        # So instead I make sure that the sys.exit(0) is called twice
        self.assertEqual(len(self.sys.mock_calls), 2)
