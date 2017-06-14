#!/usr/bin/env python

import datetime

from launchpadlib.launchpad import Launchpad
launchpad = Launchpad.login_with('openstack-bugs', 'production')

PROJECT = "devstack"

project = launchpad.projects[PROJECT]


def delta(date_value):
    delta = datetime.date.today() - date_value.date()
    return delta.days


class LPBug(object):
    def __init__(self, task, project=PROJECT):
        self._project = project
        self.bug = launchpad.load(task.bug_link)
        for task in self.bug.bug_tasks:
            if task.bug_target_name == project:
                self.task = task

    @property
    def title(self):
        return self.bug.title

    @property
    def status(self):
        return self.task.status

    @status.setter
    def status(self, value):
        self.task.value = value
        self.task.lp_save()

    def add_comment(self, msg):
        self.bug.newMessage(content=msg)

    @property
    def age(self):
        return delta(self.bug.date_created)

    @property
    def last_updated(self):
        return delta(self.bug.date_last_updated)

    def __repr__(self):
        return '<LPBug title="%s" status="%s" link="%s">' % (self.title, self.status, self.task.web_link)


message = """
This bug was last updated over 180 days ago, as devstack is a fast moving project
and we'd like to get the tracker down to currently actionable bugs, this is getting
marked as Invalid. If the issue still exists, please feel free to reopen it.
"""

for task in project.searchTasks(
        omit_duplicates=True,
        order_by='-importance'):
    bug = LPBug(task)
    if bug.last_updated > 180:
        print "WOULD CLOSE: Last Updated: %s" % bug.last_updated
        bug.add_comment(message)
        bug.status = "Invalid"
    print bug
