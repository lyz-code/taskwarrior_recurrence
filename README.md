# Taskwarrior Recurrence

As stated [here](https://taskwarrior.org/docs/design/recurrence.html) the
recurrence in taskwarrior has several issues, such as:

* If you move the due date of a recurrent task you mess up all the future tasks.
* The mask attribute grows unbounded.
* Only strict recurrence cycles are supported. The example of mowing the lawn is
  that you want to mow the lawn every seven days, but when you are four days
  late mowing the lawn, the next mowing should be in seven days, not in three.
* Instances generated on one machine and then synced, may collide with equivalent
  unsynced instances tasks on another device, because the UUIDs are different.
* You cannot wait a recurring task and have that wait period propagate to all
  other child tasks.
* Task instances cannot individually expire.

Based on that document I created some hooks to fix it.

**Warning!:** If you use this recurrence method you'll only have one pending
recurring child. That means that if the task is overdue and the next task should
have been created, it wont till you complete or delete the living child.

## Install

As we are going to use our own recurrence method, we have to set on our `taskrc`

```
recurrence=no
report.recurring.filter=status:recurring
uda.rtype.label=Recur.Type
uda.rtype.type=string
uda.rtype.values=chained,periodic
uda.r.label=R
uda.r.type=string
```

```bash
cd ~/.task
mkdir hooks
git clone https://git.digitales.cslabrecha.org/lyz/taskwarrior_recurrence
cd taskwarrior_recurrence/taskwarrior_recurrence
ln -s main.py ../../
ln -s on_add.py ../../on-add.fix-recurrence.py
ln -s on_exit.py ../../on-exit.fix-recurrence.py
```

## Chained recurrence

If you delete or complete a chained task causes the next chained instance to be
synthesized.  This gives the illusion that the due date is simply pushed out to
(now + template.recur).

You should use this kind of recurrence for the tasks like the lawn mowing
example above.

### Create a recurrent chained task

Execute the following to create a chained recurrent task due in 3 days with
a recurrence of 2 days

```bash
task add rtype:chained r:2d due:3d 'This is a chained recurrent task'
```

This will create a recurrent hidden parent task and the first child chained
task.

Each time you complete or delete a children chained task this hook will create
a new task with the due, wait and schedule attributes set to:

* due:         instance[N-1].end + template.recur
* wait:        instance.due + (template.due - template.wait)
* scheduled:   instance.due + (template.due - template.scheduled)

### Modify a recurrent chained task

If you want to edit the recurrence, wait, or schedule of a chained task you have
to do it on the parent. And the next child will propagate the changes.

Currently it's not supported the automatic modification of the living child. So
your best choice is to modify the parent and delete the child.

### Delete a recurrent chained task

If you want to remove a recurrent chained task, you have to delete the parent.
This will automatically delete all the children.

If you try to complete a parent task it will result in an error, because
recurrent tasks can't be completed.

## Periodic recurrence

If you delete or complete a periodic task, it causes the next periodic instance to be
synthesized.

Imagine you have a periodic task that is due in 2 days with a recurrence of
2 days. The next task will have a due of 4d

You should use this kind of recurrence for the tasks that have a fixed date with
fixed recurrence, for example birthdays.

### Create a recurrent periodic task

Execute the following to create a periodic recurrent task due in 3 days with
a recurrence of 2 days

```bash
task add rtype:periodic r:2d due:3d 'This is a periodic recurrent task'
```

This will create a recurrent hidden parent task and the first child chained
task.

Each time you complete or delete a children chained task this hook will create
a new task with the due, wait and schedule attributes set to:

* due:         template.due + (N * template.recur)
* wait:        instance.due + (template.due - template.wait)
* scheduled:   instance.due + (template.due - template.scheduled)

Resulting of a `due` of the next instance of the periodic task since today. So
`N` is incremented by one till it finds a `due` > `now`.

### Modify a recurrent periodic task

If you want to edit the recurrence, wait, or schedule of a periodic task you have
to do it on the parent. And the next child will propagate the changes.

Currently it's not supported the automatic modification of the living child. So
your best choice is to modify the parent and delete the child.

### Delete a recurrent periodic task

If you want to remove a recurrent periodic task, you have to delete the parent.
This will automatically delete all the children.

If you try to complete a parent task it will result in an error, because
recurrent tasks can't be completed.

## Test

To run the tests first install `tox`

```bash
pip3 install tox
```

And then run the tests

```bash
unset TASKRC
tox
```

## FAQ

### I get a lot of errors on the tests

Maybe you've got the `TASKRC` environmental variable set.

Unset it with... `unset TASKRC` `ᕙ(⇀‸↼‶)ᕗ`

### Why didn't you use the `recur` attribute?

I tried to use it but it didn't do what I expected, therefore I'll use the `r`
attribute.

To make the parent task disappear I've set the `recur == r` but with the
`recurrence=no` in the config it will do nothing.

To visualize the tasks you should show the recur with the r value

## Todo

* Refactor the tests of `TestProcessRecurrentTask` and `TestChildChainedTask`,
changing the mocks of tasklib for actual temporary objects. This has already
been implemented in `TestChildPeriodicTask`.

## Author

lyz [at] riseup net
