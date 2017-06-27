#!/usr/bin/env python

import argparse

import openstack_bugs
from openstack_bugs.messages import DISCOVERED_STACK_VERS, NO_STACK_VERS_FOUND

from launchpadlib.launchpad import Launchpad

LPSTATUS = ('New', 'Confirmed', 'Triaged', 'In Progress', 'Incomplete')
LPIMPORTANCE = ('Critical', 'High', 'Medium', 'Undecided', 'Low', 'Wishlist')

ALL_STATUS = ["New",
              "In Progress",
              "Incomplete",
              "Confirmed",
              "Triaged"]

NO_REVIEWS = """
This bug is not In Progress, and has no open patches in the
comments, so it is being unassigned. Please take ownership of bugs
if you have a patch to submit for them to ensure that
people are not discouraged from looking at these bugs.
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Tag bugs that need more info")
    parser.add_argument('--project', required=True,
                        help='The project to act on')
    parser.add_argument('--search',
                        help='Custom search terms for bug')
    parser.add_argument('--age', default=0,
                        help=('Bugs that are less than this number of '
                              'days old require versions to not be marked '
                              'incomplete. Default: 0'))
    parser.add_argument('--dryrun', action="store_true", default=False)
    parser.add_argument('--verbose', action="store_true", default=False)
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
            bug = openstack_bugs.LPBug(task, launchpad, project=args.project)
            print(bug)
            version = openstack_bugs.discover_stack_version(
                args.project, bug.description)
            if args.verbose:
                print(bug.description)

            tags = bug.tags
            if version is not None:
                new_tag = "openstack-version.%s" % version
                print("Found tags: %s" % tags)
                if new_tag not in tags:
                    print("Adding %s to tags" % new_tag)
                    if not args.dryrun:
                        bug.add_tag(new_tag)
                        bug.add_comment(DISCOVERED_STACK_VERS
                                        % (version, args.project))
            if version is None and args.age and bug.age <= args.age:
                if (bug.status != "Incomplete" and
                    "needs.openstack-version" not in bug.tags):
                    print("Marking bug incomplete - no openstack version specified")
                    if not args.dryrun:
                        if bug.add_tag("needs.openstack-version"):
                            bug.status = "Incomplete"
                            bug.add_comment(NO_STACK_VERS_FOUND
                                            % (args.project))
            if args.verbose:
                # make it easier to sort out bugs
                print("\n\n")

        except Exception as e:
            print "Exception: %s" % e
    print "Total found: %s, would fix %s, in prog %s" % (count, fixed, inprog)


if __name__ == "__main__":
    main()
