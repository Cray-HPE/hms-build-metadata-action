#! /usr/bin/env python3

#
# MIT License
#
# (C) Copyright [2021-2022] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

import time
import subprocess
import re
import os

STABLE_STRATEGIES=["branch", "tag", "always", "never"]

STABLE_STRATEGY = os.getenv("STABLE_STRATEGY", "")
if STABLE_STRATEGY not in STABLE_STRATEGIES:
    print("Invalid STABLE_STRATEGY provided ({}), need to be one of [{}]".format(STABLE_STRATEGY, ', '.join(STABLE_STRATEGIES)))
    exit(1)

STABLE_BRANCHES_REGEX = os.getenv("STABLE_BRANCHES_REGEX", "")
if STABLE_STRATEGY == "branch" and STABLE_BRANCHES_REGEX == "":
    print("Error STABLE_BRANCHES_REGEX was not provided")
    exit(1)

GITHUB_REF = os.getenv("GITHUB_REF", "")
if GITHUB_REF == "":
    print("Error GITHUB_REF was not provided")
    exit(1)


# Timestamp: date +%Y%m%d%H%M%S
time_stamp = time.strftime('%Y%m%d%H%M%S',time.gmtime())

# Short Git SHA: git rev-parse HEAD | cut -c1-7
print("Getting Git SHA...")
git_env = os.environ.copy()
result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, shell=False, env=git_env)
if result.returncode != 0:
    print("Error: non-zero exit code from git:", result.returncode)
    print("stdout:", result.stdout)
    print("stderror:", result.stderr)
    exit(1)
git_sha=result.stdout.strip()[0:7]


# Branch name: git rev-parse --abbrev-ref HEAD
print("Getting Git branch...")
result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True, shell=False, env=git_env)
if result.returncode != 0:
    print("stdout:", result.stdout)
    print("stderror:", result.stderr)
    print("Error: non-zero exit code from git:", result.returncode)
    exit(1)
git_branch=result.stdout.strip()

# Determine if the build is stable or not
is_stable = False
if STABLE_STRATEGY == "branch":
    is_stable = re.compile(STABLE_BRANCHES_REGEX).match(git_branch)
elif STABLE_STRATEGY == "tag":
    is_stable = GITHUB_REF.startswith("refs/tags/v")
elif STABLE_STRATEGY == "always":
    is_stable = True
elif STABLE_STRATEGY == "never":
    is_stable = False
else:
    print("Unknown STABLE_STRATEGY provided ({})".format(STABLE_STRATEGY,))
    exit(1)


result = {}
result["timestamp"] = time_stamp
result["git-sha"] = git_sha
result["git-branch"] = git_branch
result["docker"] = "-{}.{}".format(time_stamp, git_sha)
if is_stable:
    result["is-stable"] = "true"
    result["helm"] = ""
else:
    result["is-stable"] = "false"
    result["helm"] = "-{}+{}".format(time_stamp, git_sha)

print("Stable build: ", result["is-stable"])
print("Timestamp:    ", result["timestamp"])
print("Git SHA:      ", result["git-sha"])
print("Git branch:   ", result["git-branch"])
print("Helm Suffix:  ", result["helm"])
print("Docker Suffix:", result["docker"])
print()

for name in result:
    print("::set-output name={}::{}".format(name, result[name]))
