================
 Nova Bug Tools
================

These are a set of tools to do things with the Nova bug backlog (and
possibly other backlogs) to try to help keep things manageable. All
tools work on launchpad in a live state, be careful of what you decide
to run.

Many are experimental and include half baked ideas about ways that you
might want to interact with the bugs.

Making Bug Trackers More useful
===============================

Bug trackers are useful when they are full of actionable content. For
a bug to be actionable it has to:

* be accurate - in progress really must mean the bug is being actively
  worked.
* be consistent - if something is in progress, both gerrit and lp need
  to agree on that front
* have a next step - even if that is collecting a certain bit of
  information
* surface to the right people - ideally we expose each bug to the
  right set of people to take the next step
* make manual triage more efficient - a short hand for comments that
  triggers more processing later

We can get pretty far on accuracy and consistency just through defined
algorithms, and cross checking gerrit vs. launchpad (given that the
existing tools sometimes time out).

Getting to the next step is harder, and quite hard to do with
launchpad's built in workflow. However we can build a tags based
workflow based on "needs.*" tags outside of the system, that can be as
project granular as we like. Some of these tags can be automatically
applied, like we always really do want to know version and OS, because
if the bug isn't dealt with in a year, we can guage how relevant it is
likely to be.

Surfacing to the right people also means not overwhelming people. So
individuals should easily be able to see 10 - 20 bugs they might have
real input on, and not waste time looking at bugs then realizing there
is nothing they can add to them. This can be done through functional
tags, either human applied, or possibly machine assisted.

If you start triaging bugs in bulk, you get into a flow. This bug
needs the following logs (and needs to explain to the user to upload
them, put it in an incomplete state, etc), this bug needs these tags,
this bug needs a confirmation on master, or a reproduce. However,
doing all these state changes, and explaining why you did them,
actually takes a while, as launchpad is slow, and the UI elements are
in different parts of the system. A #hashtag based set of macros for
triaging (which a bug comes through and processes later with more
specific instructions to the user) would greatly reduce human effort
on manual triage.

Mission
=======

.. note::

   This is a little redundant from above, as it was written first.

Bug triage is a thankless task. Lots of triaging is about
communicating back to users what is needed next, and communicating to
developers the readiness state of a bug. A lot of this can be machine
assisted, for instance:

* Which bugs are really In Progress (have open code), hence which bugs
  shouldn't be picked for new fixes.
* What was the platform where the bug showed up?
* What additional information do we need (some of which we should
  always ask for)

Also remembering that the likelihood of response from a bug submitter
is a decay function. If you can ask them for relevant questions within
5 minutes of them filing a bug, you might actually get answers. If it
takes over a week to get back to them, they may not have the
environment any more.

This logic is starting as a set of scripts that you run manually. This
makes it a human decision to run these tools, and the algorithms
within.

Long term the theory is that some of this logic will be triggered off
of MQTT notifications from a bit of bug activity, possibly in a
serverless environment.

Common Patterns
===============

The CLI tools provided follow a common set of patterns and require
certain cli args whenever possible (also all tools support -h to
discover args)

* --project <NAME> - the project to act upon. Required. This is in the
  form of 'nova', 'devstack', etc. Project is needed because bugs can
  be assigned to more than one project, and you have to know which
  "task" to act on.

* --search <search string> - an optional parameter that lets you put
  in a text search string to further restrict the bugs being
  returned. This is helpful if you see that things aren't working
  right with a particular bug, and want to more quickly figure out
  why.

* --dryrun - an optional argument that will prevent the tool from
  making any changes, but will tell you what it would be doing. YOU
  SHOULD ALWAYS run with --dryrun before running for real.

All changes to bug state also come with a comment in the bug that
explains why things were changed.

Existing Tools
==============

* close-old-bugs.py

  closes all bugs with no activity in the last N days as Invalid
  (where N defaults to 180 days). This is useful if your bug tracker
  is really lightly maintained, and you are declaring bankruptcy on
  old bugs.

* tag-needs-info.py

  Currently attempts to discover openstack versions, and tags things
  with 'openstack-version.$name'. Very heuristic, so not perfectly
  accurate.

  TODO: add os version detection.

  TODO: flag as incomplete with needs.openstack-version if one is not found.

* fix-in-progress-bugs.py

  Scan all in progress bugs and make sure that they've got at least
  one open review listed in the comments which demonstrates they are
  in progress. If they don't, then revert them to the last state
  before in progress and unassign them.

* unassign-non-in-progress-bugs.py

  Scan non in progress bugs. If they have an assingee and an open
  review, set them in progress. If they don't have an open review,
  unassign the bug (only In Progress bugs should have assignees). If
  an open review was found, with no assignee, set to In Progress and
  set the assignee to the last person the bug was assigned to.

  TODO: provide some grade period, i.e. 7 days, where people can take
  a bug before it is unassigned.

* find-reviews-for-bugs.py

  Scan gerrit for commits that say they are related to a bug. If the
  bug in question is not In Progress, provide a comment with the open
  reviews, and set the progress to In Progress, and set the assignee
  to the last person the bug was assigned to.
