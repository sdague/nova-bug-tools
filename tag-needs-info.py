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
              "In Progress",
              "Incomplete",
              "Confirmed",
              "Triaged"]


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
This bug is not In Progress, and has no open patches in the
comments, so it is being unassigned. Please take ownership of bugs
if you have a patch to submit for them to ensure that
people are not discouraged from looking at these bugs.
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
    def description(self):
        msg = self.bug.messages[0]
        return msg.content

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
        description="Tag bugs that need more info")
    parser.add_argument('--project', required=True,
                        help='The project to act on')
    parser.add_argument('--search',
                        help='Custom search terms for bug')
    parser.add_argument('--dryrun', action="store_true", default=False)
    parser.add_argument('--verbose', action="store_true", default=False)
    return parser.parse_args()


def version_normalize(version):
    """A set of normalizations found based on the info."""
    if not version:
        return

    version = version.rstrip().lstrip()

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
            bug = LPBug(task, launchpad, project=args.project)
            print(bug)
            # print bug.description
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
                        tags.append(new_tag)
                        bug.bug.tags = tags
                        print(bug.bug.tags)
                        bug.bug.lp_save()
                        bug.add_comment(
                            "Automatically discovered version %s in description. "
                            "If this is incorrect, please update the description "
                            "to include '%s version: ...'" % (version, args.project))
            if version is None and bug.age < 14:
                if bug.status != "Incomplete":
                    print("Marking bug incompleted as no version specified")
                    if not args.dryrun:
                        tags.append("needs.openstack-version")
                        bug.bug.tags = tags
                        bug.bug.lp_save()
                        bug.status = "Incomplete"
                        bug.add_comment(
                            "No version was found in the description, which is "
                            "required, marking as Incomplete. Please update the "
                            "bug description to include '%s version: ... '." %
                            (args.project))
            if args.verbose:
                # make it easier to sort out bugs
                print("\n\n")



            # if bug.assignee:
            #     reviews = open_reviews(bug.reviews)
            #     if reviews:
            #         inprog += 1
            #         if not args.dryrun:
            #             bug.status = "In Progress"
            #         print("... this bug is marked in progress")
            #     else:
            #         fixed += 1
            #         if not args.dryrun:
            #             bug.assignee = None
            #         print("... bug is assigned but should not be!")
        except Exception as e:
            print "Exception: %s" % e
    print "Total found: %s, would fix %s, in prog %s" % (count, fixed, inprog)


if __name__ == "__main__":
    main()
