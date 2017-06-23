#!/usr/bin/env python

import argparse
import datetime
import json
import re
import requests
import sys

from launchpadlib.launchpad import Launchpad
launchpad = Launchpad.login_with('openstack-bugs', 'production')

RE_LINK = re.compile(' https://review.openstack.org/(\d+)')


LPSTATUS = ('New', 'Confirmed', 'Triaged', 'In Progress', 'Incomplete')
LPIMPORTANCE = ('Critical', 'High', 'Medium', 'Undecided', 'Low', 'Wishlist')

ALL_STATUS = ["New",
              "Incomplete",
              "Opinion",
              "Invalid",
              "Won't Fix",
              "Expired",
              "Confirmed",
              "Triaged",
              "In Progress",
              "Fix Committed",
              "Fix Released"]



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


def open_reviews(review_nums):
    openrevs = []
    for review in review_nums:
        status = get_review_status(review)
        if status == "NEW":
            openrevs.append(review)
    return openrevs


NO_REVIEWS = """
There are no currently open reviews on this bug, changing
the status back to the previous state and unassigning. If
there are active reviews related to this bug, please include
links in comments.
"""


class LPBug(object):
    def __init__(self, task, lp, project=None):
        self._project = project
        self._activity = None
        self.bug = lp.load(task.bug_link)
        self.task = None
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

    @property
    def last_status(self):
        last = "New"
        for a in self.bug.activity:
            if a.whatchanged == ("%s: status" % self._project):
                last = a.oldvalue
        return last

    def __repr__(self):
        return '<LPBug title="%s" status="%s" link="%s">' % \
            (unicode(self.title), self.status, self.task.web_link)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mark check status on in progress bugs")
    parser.add_argument('--project', required=True,
                        help='The project to act on')
    parser.add_argument('--search',
                        help='Custom search terms for bug')
    parser.add_argument('--dryrun', action="store_true", default=False)
    return parser.parse_args()


def main():
    args = parse_args()
    launchpad = Launchpad.login_with('openstack-bugs', 'production')
    project = launchpad.projects[args.project]
    count = 0
    fixed = 0
    for task in project.searchTasks(status="In Progress",
                                search_text=args.search,
                                order_by='date_last_updated'):
        try:
            count += 1
            bug = LPBug(task, launchpad, project=args.project)
            if bug.status == "In Progress":
                reviews = open_reviews(bug.reviews)
                print(bug)
                if len(reviews) > 0:
                    print("... found open reviews")
                else:
                    print("... no open reviews, should change status")
                    fixed += 1
                    last_status = bug.last_status
                    bug.status = last_status
                    bug.add_comment(NO_REVIEWS)
                    bug.assignee = None
                    print("... changed to %s" % last_status)
        except Exception as e:
            print "Exception: %s" % e
    print "Total found: %s, would fix %s" % (count, fixed)


if __name__ == "__main__":
    main()
