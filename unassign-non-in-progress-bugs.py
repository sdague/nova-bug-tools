#!/usr/bin/env python

import argparse

from launchpadlib.launchpad import Launchpad

import openstack_bugs
from openstack_bugs.messages import NO_REVIEWS

ALL_STATUS = ["New",
              "Incomplete",
              "Confirmed",
              "Triaged"]


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
    inprog = 0
    for task in project.searchTasks(status=ALL_STATUS,
                                search_text=args.search,
                                order_by='date_last_updated'):
        try:
            count += 1
            inprog
            bug = openstack_bugs.LPBug(task, launchpad, project=args.project)
            print(bug)
            if bug.assignee:
                reviews = openstack_bugs.open_reviews(bug.reviews)
                if reviews:
                    inprog += 1
                    if not args.dryrun:
                        bug.status = "In Progress"
                    print("... this bug is marked in progress")
                else:
                    fixed += 1
                    if not args.dryrun:
                        bug.assignee = None
                        bug.add_comment(NO_REVIEWS)
                    print("... bug is assigned but should not be!")
        except Exception as e:
            print "Exception: %s" % e
    print "Total found: %s, would fix %s, in prog %s" % (count, fixed, inprog)


if __name__ == "__main__":
    main()
