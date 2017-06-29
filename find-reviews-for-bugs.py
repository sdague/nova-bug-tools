#!/usr/bin/env python

import argparse

from launchpadlib.launchpad import Launchpad

import openstack_bugs
from openstack_bugs.messages import NO_REVIEWS

import re
BUG_REGEX = re.compile(".*bug\:\s*\#?(\d+)", re.IGNORECASE)

URL = ("https://review.openstack.org/changes/?q=status:open+project:%s"
       "+message:%%22bug:%%22&o=CURRENT_COMMIT&o=CURRENT_REVISION")


def find_reviews_for_bugs(project):
    import requests
    import json
    r = requests.get(URL % project)
    results = json.loads(r.text[4:])
    bug_rev_mapping = {}
    for res in results:
        revision = res["revisions"].values()[0]
        message = revision["commit"]["message"]
        bugs = BUG_REGEX.findall(message)
        # print "%s => %s" % (res["_number"], bugs)
        # if len(bugs) < 1:
        #     print "No bugs found in message: %s" % message
        for bug in bugs:
            if bug in bug_rev_mapping:
                bug_rev_mapping[bug].append((res["branch"], res["_number"]))
            else:
                bug_rev_mapping[bug] = [(res["branch"], res["_number"])]
    return bug_rev_mapping


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
    # project = launchpad.projects[args.project]
    bugs = find_reviews_for_bugs("openstack/%s" % args.project)
    for bug_id, reviews in bugs.items():
        try:
            bug = openstack_bugs.LPBug(
                "https://api.launchpad.net/1.0/bugs/%s" % (bug_id),
                launchpad, args.project)
            if bug.task is None:
                print "Not a Nova Bug!"
                continue
            if bug.status not in ("In Progress", "Fix Released"):
                print "Bug: %s " % bug
                print "   Reviews: %s" % reviews
                rev_msg = ""
                for rev in reviews:
                    rev_msg += ("review: https://review.openstack.org/%s "
                                "in branch: %s\n" % (
                                    rev[1], rev[0]))
                msg = ("Found open reviews for this bug in gerrit, setting "
                       "to In Progress. \n\n" + rev_msg)
                print msg
                if not args.dryrun:
                    bug.status = "In Progress"
                    bug.revert_to_last_assignee()
                    bug.add_comment(msg)
                    print("... set to In Progress")

        except Exception as e:
            print "Failed! https://bugs.launchpad.net/nova/+bug/%s => %s" % (bug_id, e)


if __name__ == "__main__":
    main()
