import datetime
import re


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
