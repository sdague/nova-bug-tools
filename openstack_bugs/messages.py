# A list of messages for useful things

DISCOVERED_STACK_VERS = (
    "Automatically discovered version %s in description. "
    "If this is incorrect, please update the description "
    "to include '%s version: ...'")

NO_STACK_VERS_FOUND = (
    "No version was found in the description, which is "
    "required, marking as Incomplete. Please update the "
    "bug description to include '%s version: ... '.")

NOT_INPROGRESS = (
    "This bug is not In Progress, and has no open patches in the "
    "comments, so it is being unassigned. Please do not take ownership of "
    "bugs if you have a patch to submit for them to ensure that people are "
    "not discouraged from looking at these bugs.")

NO_REVIEWS = (
    "There are no currently open reviews on this bug, changing "
    "the status back to the previous state and unassigning. If "
    "there are active reviews related to this bug, please include "
    "links in comments. ")

INACTIVE_BUG = (
    "This bug was last updated over %s days ago, as %s "
    "is a fast moving project and we'd like to get the tracker down to "
    "currently actionable bugs, this is getting marked as Invalid. If the "
    "issue still exists, please feel free to reopen it.")
