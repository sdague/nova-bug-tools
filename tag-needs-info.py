#!/usr/bin/env python

import argparse
import json
import re
import requests

import openstack_bugs
from openstack_bugs.messages import DISCOVERED_STACK_VERS, NO_STACK_VERS_FOUND

from launchpadlib.launchpad import Launchpad
launchpad = Launchpad.login_with('openstack-bugs', 'production')

LPSTATUS = ('New', 'Confirmed', 'Triaged', 'In Progress', 'Incomplete')
LPIMPORTANCE = ('Critical', 'High', 'Medium', 'Undecided', 'Low', 'Wishlist')

ALL_STATUS = ["New",
              "In Progress",
              "Incomplete",
              "Confirmed",
              "Triaged"]


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


def version_normalize(version):
    """A set of normalizations found based on the info."""
    if not version:
        return

    version = version.rstrip().lstrip()
    # split off some very standard compound versions markers
    version = version.split(" ")[0].split("(")[0]
    # this is a url and not even a git sha
    if len(version) > 40:
        return None

    # master is not useful, given that it requires understanding point
    # in time of the bug. Maybe some day we can manage to make this
    # detect when it was, and bucket it. That's a whole different beast.
    if version.lower() == "master":
        return None

    mapping = {
        "2013.1": "grizzly",
        "2013.2": "havana",
        "2014.1": "icehouse",
        "2014.2": "juno",
        "2015.1": "kilo",
        "2015.2": "liberty",
        "12.": "liberty",
        "13.": "mitaka",
        "14.": "newton",
        "15.": "ocata",
        "16.": "pike"
    }

    for k, v in mapping.items():
        if version.startswith(k):
            return v

    if version.lower() in mapping.values():
        return version.lower()

    if version.startswith("stable/"):
        strip_vers = version[7:]
        if strip_vers.lower() in mapping.values():
            return strip_vers.lower()

    return version


def discover_stack_version(project, desc):
    known_versions = ("grizzly", "havana", "icehouse", "juno",
                      "kilo", "liberty", "mitaka", "newton", "ocata", "pike")
    #
    # the ideal version is Openstack Version: ....
    matches = (
        "(^|\n)openstack\s*version\s*:(?P<version>.*)",  # ideal version
        "(^|\n)%s(\s*version)?\s*:(?P<version>.*)" % project,  # nova version
        "(^|\n)openstack-%s-common-(?P<version>.*)" % project,  # rhel version
        "(^|\n)openstack-%s-compute-(?P<version>.*)" % project,  # rhel version
        r"\b%s-common\s+\d\:(?P<version>.*)" % project,  # ubuntu dpkg
                                                         # -l version
        r"(?P<version>\b(%s)\b)" % ("|".join(known_versions)),  # keywords
    )
    found_version = None
    for attempt in matches:
        m = re.search(attempt, desc, re.IGNORECASE)
        if m:
            found_version = m.group('version')
            if found_version:
                break
    return version_normalize(found_version)


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
            version = discover_stack_version(args.project, bug.description)
            if args.verbose:
                print(bug.description)

            tags = list(bug.bug.tags)
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
