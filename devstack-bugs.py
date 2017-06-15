#!/usr/bin/env python

import datetime
import json
import re
import requests

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


def get_review_status(review_number):
    """Return status of a given review number."""
    r = requests.get("https://review.openstack.org:443/changes/%s"
                     % review_number)
    # strip off first few chars because 'the JSON response body starts with a
    # magic prefix line that must be stripped before feeding the rest of the
    # response body to a JSON parser'
    # https://review.openstack.org/Documentation/rest-api.html
    status = None
    try:
        status = json.loads(r.text[4:])['status']
    except ValueError:
        status = r.text
    return status

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
        if bug.last_updated > 180:
            print "WOULD CLOSE: Last Updated: %s" % bug.last_updated
            bug.add_comment(message)
            bug.status = "Invalid"
        print bug
    except Exception as e:
        print "ERROR: couldn't mark %s as invalid %s" % (bug, e)

    if bug.assignee:
        if not bug.reviews:
            print "Unassigning the bug"
            bug.add_comment("No reviews found in this bug, unassigning. Please add a comment with active reviews before assigning an individual, or tag the bug in the gerrit review, which will do that automatically. We try not to assign bugs without patches as that discourages other folks from looking into bugs.")
            bug.assignee = None
            if bug.status == "In Progress":
                bug.status = "New"
        else:
            open_reviews = False
            for r in bug.reviews:
                status = get_review_status(r)
                print "Status for %s is %s" % (r, status)
                if status == "NEW":
                    open_reviews = True
            if open_reviews is False:
                print "Unassigning the bug"
                bug.add_comment("No open reviews found in this bug, unassigning. Please add a comment with active reviews before assigning an individual, or tag the bug in the gerrit review, which will do that automatically. We try not to assign bugs without patches as that discourages other folks from looking into bugs.")
                bug.assignee = None
                if bug.status == "In Progress":
                    bug.status = "New"

            print "Open Reviews: %s" % open_reviews



for task in project.searchTasks(status=["Fix Committed"],
                omit_duplicates=True,
        order_by='-importance'):
    bug = LPBug(task)
    print bug
    bug.status = "Fix Released"
