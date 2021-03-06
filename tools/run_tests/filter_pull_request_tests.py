#!/usr/bin/env python2.7
# Copyright 2015, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Filter out tests based on file differences compared to merge target branch"""

import re
from subprocess import call, check_output


class TestSuite:
  """
  Contains label to identify job as belonging to this test suite and
  triggers to identify if changed files are relevant
  """
  def __init__(self, labels):
    """
    Build TestSuite to group tests based on labeling
    :param label: strings that should match a jobs's platform, config, language, or test group
    """
    self.triggers = []
    self.labels = labels

  def add_trigger(self, trigger):
    """
    Add a regex to list of triggers that determine if a changed file should run tests
    :param trigger: regex matching file relevant to tests
    """
    self.triggers.append(trigger)


# Create test suites
_SANITY_TEST_SUITE = TestSuite(['sanity'])
_CORE_TEST_SUITE = TestSuite(['c'])
_CPP_TEST_SUITE = TestSuite(['c++'])
_CSHARP_TEST_SUITE = TestSuite(['csharp'])
_NODE_TEST_SUITE = TestSuite(['node'])
_OBJC_TEST_SUITE = TestSuite(['objc'])
_PHP_TEST_SUITE = TestSuite(['php', 'php7'])
_PYTHON_TEST_SUITE = TestSuite(['python'])
_RUBY_TEST_SUITE = TestSuite(['ruby'])
_LINUX_TEST_SUITE = TestSuite(['linux'])
_WINDOWS_TEST_SUITE = TestSuite(['windows'])
_MACOS_TEST_SUITE = TestSuite(['macos'])
_ALL_TEST_SUITES = [_SANITY_TEST_SUITE, _CORE_TEST_SUITE, _CPP_TEST_SUITE,
                    _CSHARP_TEST_SUITE, _NODE_TEST_SUITE, _OBJC_TEST_SUITE,
                    _PHP_TEST_SUITE, _PYTHON_TEST_SUITE, _RUBY_TEST_SUITE,
                    _LINUX_TEST_SUITE, _WINDOWS_TEST_SUITE, _MACOS_TEST_SUITE]

# Dictionary of whitelistable files where the key is a regex matching changed files
# and the value is a list of tests that should be run. An empty list means that
# the changed files should not trigger any tests. Any changed file that does not
# match any of these regexes will trigger all tests
_WHITELIST_DICT = {
  '^doc/': [],
  '^examples/': [],
  '^include/grpc\+\+/': [_CPP_TEST_SUITE],
  '^summerofcode/': [],
  '^src/cpp/': [_CPP_TEST_SUITE],
  '^src/csharp/': [_CSHARP_TEST_SUITE],
  '^src/node/': [_NODE_TEST_SUITE],
  '^src/objective\-c/': [_OBJC_TEST_SUITE],
  '^src/php/': [_PHP_TEST_SUITE],
  '^src/python/': [_PYTHON_TEST_SUITE],
  '^src/ruby/': [_RUBY_TEST_SUITE],
  '^templates/': [_SANITY_TEST_SUITE],
  '^test/core/': [_CORE_TEST_SUITE],
  '^test/cpp/': [_CPP_TEST_SUITE],
  '^test/distrib/cpp/': [_CPP_TEST_SUITE],
  '^test/distrib/csharp/': [_CSHARP_TEST_SUITE],
  '^test/distrib/node/': [_NODE_TEST_SUITE],
  '^test/distrib/php/': [_PHP_TEST_SUITE],
  '^test/distrib/python/': [_PYTHON_TEST_SUITE],
  '^test/distrib/ruby/': [_RUBY_TEST_SUITE],
  '^vsprojects/': [_WINDOWS_TEST_SUITE],
  'binding\.gyp$': [_NODE_TEST_SUITE],
  'composer\.json$': [_PHP_TEST_SUITE],
  'config\.m4$': [_PHP_TEST_SUITE],
  'CONTRIBUTING\.md$': [],
  'Gemfile$': [_RUBY_TEST_SUITE],
  'grpc.def$': [_WINDOWS_TEST_SUITE],
  'grpc\.gemspec$': [_RUBY_TEST_SUITE],
  'gRPC\.podspec$': [_OBJC_TEST_SUITE],
  'gRPC\-Core\.podspec$': [_OBJC_TEST_SUITE],
  'gRPC\-ProtoRPC\.podspec$': [_OBJC_TEST_SUITE],
  'gRPC\-RxLibrary\.podspec$': [_OBJC_TEST_SUITE],
  'INSTALL\.md$': [],
  'LICENSE$': [],
  'MANIFEST\.md$': [],
  'package\.json$': [_PHP_TEST_SUITE],
  'package\.xml$': [_PHP_TEST_SUITE],
  'PATENTS$': [],
  'PYTHON\-MANIFEST\.in$': [_PYTHON_TEST_SUITE],
  'README\.md$': [],
  'requirements\.txt$': [_PYTHON_TEST_SUITE],
  'setup\.cfg$': [_PYTHON_TEST_SUITE],
  'setup\.py$': [_PYTHON_TEST_SUITE]
}

# Add all triggers to their respective test suites
for trigger, test_suites in _WHITELIST_DICT.iteritems():
  for test_suite in test_suites:
    test_suite.add_trigger(trigger)


def _get_changed_files(base_branch):
  """
  Get list of changed files between current branch and base of target merge branch
  """
  # Get file changes between branch and merge-base of specified branch
  # Not combined to be Windows friendly
  base_commit = check_output(["git", "merge-base", base_branch, "HEAD"]).rstrip()
  return check_output(["git", "diff", base_commit, "--name-only"]).splitlines()


def _can_skip_tests(file_names, triggers):
  """
  Determines if tests are skippable based on if all files do not match list of regexes
  :param file_names: list of changed files generated by _get_changed_files()
  :param triggers: list of regexes matching file name that indicates tests should be run
  :return: safe to skip tests
  """
  for file_name in file_names:
    if any(re.match(trigger, file_name) for trigger in triggers):
      return False
  return True


def _remove_irrelevant_tests(tests, skippable_labels):
  """
  Filters out tests by config or language - will not remove sanitizer tests
  :param tests: list of all tests generated by run_tests_matrix.py
  :param skippable_labels: list of languages and platforms with skippable tests
  :return: list of relevant tests
  """
  # test.labels[0] is platform and test.labels[2] is language
  # We skip a test if both are considered safe to skip
  return [test for test in tests if test.labels[0] not in skippable_labels or \
          test.labels[2] not in skippable_labels]


def filter_tests(tests, base_branch):
  """
  Filters out tests that are safe to ignore
  :param tests: list of all tests generated by run_tests_matrix.py
  :return: list of relevant tests
  """
  print("Finding file differences between gRPC %s branch and pull request...\n" % base_branch)
  changed_files = _get_changed_files(base_branch)
  for changed_file in changed_files:
    print(changed_file)
  print

  # Regex that combines all keys in _WHITELIST_DICT
  all_triggers = "(" + ")|(".join(_WHITELIST_DICT.keys()) + ")"
  # Check if all tests have to be run
  for changed_file in changed_files:
    if not re.match(all_triggers, changed_file):
      return(tests)
  # Figure out which language and platform tests to run
  skippable_labels = []
  for test_suite in _ALL_TEST_SUITES:
    if _can_skip_tests(changed_files, test_suite.triggers):
      for label in test_suite.labels:
        print("  Filtering %s tests" % label)
        skippable_labels.append(label)

  tests = _remove_irrelevant_tests(tests, skippable_labels)
  return tests
