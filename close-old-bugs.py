#!/usr/bin/env python

import argparse

import openstack_bugs
from openstack_bugs.messages import INACTIVE_BUG

from launchpadlib.launchpad import Launchpad

LPSTATUS = ('New', 'Confirmed', 'Triaged', 'In Progress', 'Incomplete')


def parse_args():
    parser = argparse.ArgumentParser(
        description="Close bugs older than certain times")
    parser.add_argument('--project', required=True,
                        help='The project to act on')
    parser.add_argument('--search',
                        help='Custom search terms for bug')
    parser.add_argument('--no-activity', default=180,
                        help=('Bugs that have no activity in the last N days '
                              'will be closed. Default: 180'))
    parser.add_argument('--dryrun', action="store_true", default=False)
    parser.add_argument('--verbose', action="store_true", default=False)
    return parser.parse_args()


def main():
    args = parse_args()
    launchpad = Launchpad.login_with('openstack-bugs', 'production')
    project = launchpad.projects[args.project]
    count = 0
    fixed = 0

    for task in project.searchTasks(status=LPSTATUS,
                                    search_text=args.search,
                                    omit_duplicates=True,
                                    order_by='date_last_updated'):
        bug = openstack_bugs.LPBug(task, launchpad, args.project)
        count += 1
        try:
            if bug.last_updated > 180:
                print(bug)
                print("WOULD CLOSE: Last Updated: %s" % bug.last_updated)
                fixed += 1
                if not args.dryrun:
                    bug.add_comment(INACTIVE_BUG %
                                    (args.no_activity, args.project))
                    bug.status = "Invalid"
        except Exception as e:
            print "ERROR: couldn't mark %s as invalid %s" % (bug, e)
    print "Total found: %s, closed %s" % (count, fixed)


if __name__ == "__main__":
    main()
