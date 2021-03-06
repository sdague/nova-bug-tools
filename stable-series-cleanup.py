#!/usr/bin/env python
#
#

import argparse
import datetime
import json
import re
import requests
import sys


from launchpadlib.launchpad import Launchpad
RE_LINK = re.compile(' https://review.openstack.org/(\d+)')

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


class LPBug(object):
    def __init__(self, task, lp, project=None):
        self._project = project
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

    def __repr__(self):
        return '<LPBug title="%s" status="%s" link="%s">' % \
            (unicode(self.title), self.status, self.task.web_link)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Set status correctly on stable series bugs")
    parser.add_argument('--project', required=True,
                        help='The project to act on')
    parser.add_argument('--series', required=True,
                        help='The series to act on (e.g. liberty, mitaka)')
    parser.add_argument('--since', required=True,
                        help='Date to start with')
    parser.add_argument('--close-all', action="store_true", default=False)
    parser.add_argument('--dryrun', action="store_true", default=False)
    return parser.parse_args()


def main():
    args = parse_args()
    launchpad = Launchpad.login_with('openstack-bugs', 'production')
    project = launchpad.projects[args.project]
    count = 0
    for task in project.searchTasks(status=ALL_STATUS,
                                modified_since=args.since,
                                order_by='date_last_updated'):
        try:
            count += 1
            bug = LPBug(task, launchpad,
                        project=("%s/%s" % (args.project, args.series)))
            if bug.task:
                print "Found a %s task: %s (%d)" % (args.series, bug, count)
                # we've found something related here
                if bug.status == "Fix Committed":
                    print "Marking %s - FIX RELEASED" % bug
                    if not args.dryrun:
                        bug.status = "Fix Released"
                elif args.close_all and not bug.task.is_complete:
                    print "Marking %s - WON'T FIX" % bug
                    if not args.dryrun:
                        bug.status = "Won't Fix"
        except Exception as e:
            print "Exception: %s" % e


if __name__ == "__main__":
    main()
