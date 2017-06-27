import datetime
import re
import json
import requests


RE_LINK = re.compile(' https://review.openstack.org/(\d+)')


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
    """Figure out which of the reviews are open."""
    openrevs = []
    for review in review_nums:
        status = get_review_status(review)
        if status == "NEW":
            openrevs.append(review)
    return openrevs


def version_normalize(version):
    """A set of normalizations found based on the info.

    This normalizes data based on the project in question to get back
    to an openstack release for tag name. It's hardcoded to nova after
    we change versioning schemes.

    TODO(sdague): project specific mapping.

    """
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
    """Discover the OpenStack Version.

    This attempts to pillage the bug description looking for things
    that might indicate the version. We do these in sequence as the
    ones near the top are a lot more trust worthy. Eventually there
    should probably be some scoring system here.
    """
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
        return msg.content.encode("utf-8")

    @property
    def tags(self):
        return list(self.bug.tags)

    @tags.setter
    def tags(self, tag_list):
        self.bug.tags = tag_list
        self.bug.lp_save()

    def add_tag(self, tag):
        # return True if we add a tag, False if we don't
        tags = self.tags
        if tag not in tags:
            tags.append(tag)
            self.tags = tags
            return True
        return False

    def remove_tags_by_regex(self, regex):
        tags = self.tags
        new_tags = filter(lambda x: not re.search(regex, x), tags)
        if tags != new_tags:
            self.tags = new_tags

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
