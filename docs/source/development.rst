.. _development:

Development
==============

Testing
-------

It is recommended use Python 3.7/3.8 for test due to some conflicts in 3.9.

Install test requirements:

.. code-block:: console

  pip install -r test-requirements.txt


Use the following commands to check Maigret:

.. code-block:: console

  # run linter and typing checks
  # order of checks%
  # - critical syntax errors or undefined names
  # - flake checks
  # - mypy checks
  make lint

  # run testing with coverage html report
  # current test coverage is 60%
  make text

  # open html report
  open htmlcov/index.html


How to publish new version of Maigret
-------------------------------------

**Collaborats rights are requires, write Soxoj to get them**.

For new version publishing you must create a new branch in repository
with a bumped version number and actual changelog first. After it you
must create a release, and GitHub action automatically create a new 
PyPi package. 

- New branch example: https://github.com/soxoj/maigret/commit/e520418f6a25d7edacde2d73b41a8ae7c80ddf39
- Release example: https://github.com/soxoj/maigret/releases/tag/v0.4.1

1. Make a new branch locally with a new version name. Check the current version number here: https://pypi.org/project/maigret/.
**Increase only patch version (third number)** if there are no breaking changes.

.. code-block:: console

  git checkout -b 0.4.0

2. Update Maigret version in three files manually:

- setup.py
- maigret/__version__.py 
- docs/source/conf.py 

3. Create a new empty text section in the beginning of the file `CHANGELOG.md` with a current date:

.. code-block:: console

  ## [0.4.0] - 2022-01-03

4. Get auto-generate release notes:

- Open https://github.com/soxoj/maigret/releases/new
- Click `Choose a tag`, enter `v0.4.0` (your version)
- Click `Create new tag`
- Press `+ Auto-generate release notes`
- Copy all the text from description text field below
- Paste it to empty text section in `CHANGELOG.txt`
- Remove redundant lines `## What's Changed` and `## New Contributors` section if it exists
- *Close the new release page*

5. Commit all the changes, push, make pull request

.. code-block:: console

  git add -p
  git commit -m 'Bump to YOUR VERSION'
  git push origin head


6. Merge pull request

7. Create new release

- Open https://github.com/soxoj/maigret/releases/new again
- Click `Choose a tag`
- Enter actual version in format `v0.4.0`
- Also enter actual version in the field `Release title` 
- Click `Create new tag`
- Press `+ Auto-generate release notes`
- **Press "Publish release" button**

8. That's all, now you can simply wait push to PyPi. You can monitor it in Action page: https://github.com/soxoj/maigret/actions/workflows/python-publish.yml