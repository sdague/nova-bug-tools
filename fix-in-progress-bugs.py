#!/usr/bin/env python

import argparse

from launchpadlib.launchpad import Launchpad

import openstack_bugs
from openstack_bugs.messages import NO_REVIEWS


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
            bug = openstack_bugs.LPBug(task, launchpad, project=args.project)
            if bug.status == "In Progress":
                reviews = openstack_bugs.open_reviews(bug.reviews)
                print(bug)
                if len(reviews) > 0:
                    print("... found open reviews")
                else:
                    print("... no open reviews, should change status")
                    fixed += 1
                    last_status = bug.last_status
                    if not args.dryrun:
                        bug.status = last_status
                        bug.add_comment(NO_REVIEWS)
                        bug.assignee = None
                    print("... changed to %s" % last_status)
        except Exception as e:
            print "Exception: %s" % e
    print "Total found: %s, would fix %s" % (count, fixed)


if __name__ == "__main__":
    main()
