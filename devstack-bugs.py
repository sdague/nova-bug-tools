#!/usr/bin/env python

import datetime
import re

from launchpadlib.launchpad import Launchpad
launchpad = Launchpad.login_with('openstack-bugs', 'production')

PROJECT = "devstack"
RE_LINK = re.compile(' https://review.openstack.org/(\d+)')


project = launchpad.projects[PROJECT]
LPSTATUS = ('New', 'Confirmed', 'Triaged', 'In Progress', 'Incomplete')
LPIMPORTANCE = ('Critical', 'High', 'Medium', 'Undecided', 'Low', 'Wishlist')

def delta(date_value):
    delta = datetime.date.today() - date_value.date()
    return delta.days

def get_reviews_from_bug(bug):
    """Return a list of gerrit reviews extracted from the bug's comments."""
    reviews = set()
    for comment in bug.messages:
        reviews |= set(RE_LINK.findall(comment.content))
    return reviews


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
        self.task.status = value
        self.task.lp_save()

    def add_comment(self, msg):
        self.bug.newMessage(content=msg)

    @property
    def age(self):
        return delta(self.bug.date_created)

    @property
    def last_updated(self):
        return delta(self.bug.date_last_updated)

    @property
    def assignee(self):
        return self.task.assignee

    @assignee.setter
    def assignee(self, name):
        self.task.assignee = name
        self.task.lp_save()

    @property
    def reviews(self):
        return get_reviews_from_bug(self.bug)

    def __repr__(self):
        return '<LPBug title="%s" status="%s" link="%s">' % (unicode(self.title), self.status, self.task.web_link)


message = """This %s bug was last updated over 180 days ago, as %s
is a fast moving project and we'd like to get the tracker down to
currently actionable bugs, this is getting marked as Invalid. If the
issue still exists, please feel free to reopen it.""" % (PROJECT, PROJECT)

for task in project.searchTasks(status=LPSTATUS, importance=LPIMPORTANCE,
        omit_duplicates=True,
        order_by='date_last_updated'):
    bug = LPBug(task)
    try:
        print bug
        if bug.last_updated > 180:
            print "WOULD CLOSE: Last Updated: %s" % bug.last_updated
            bug.add_comment(message)
            bug.status = "Invalid"
    except Exception as e:
        print "ERROR: couldn't mark %s as invalid %s" % (bug, e)

    if bug.assignee and not bug.reviews:
        print "Unassigning the bug"
        bug.add_comment("No reviews found in this bug, unassigning. Please add a comment with active reviews before assigning an individual, or tag the bug in the gerrit review, which will do that automatically")
        bug.assignee = None
        if bug.status == "In Progress":
            bug.status = "New"



for task in project.searchTasks(status=["Fix Committed"],
                omit_duplicates=True,
        order_by='-importance'):
    bug = LPBug(task)
    print bug
    bug.status = "Fix Released"
