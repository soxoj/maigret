.. _development:

Development
==============

Frequently Asked Questions
--------------------------

1. Where to find the list of supported sites?

The human-readable list of supported sites is available in the `sites.md <https://github.com/soxoj/maigret/blob/main/sites.md>`_ file in the repository.
It's been generated automatically from the main JSON file with the list of supported sites.

The machine-readable JSON file with the list of supported sites is available in the
`data.json <https://github.com/soxoj/maigret/blob/main/maigret/resources/data.json>`_ file in the directory `resources`.

2. Which methods to check the account presence are supported?

The supported methods (``checkType`` values in ``data.json``) are:

- ``message`` - the most reliable method, checks if any string from ``presenceStrs`` is present and none of the strings from ``absenceStrs`` are present in the HTML response
- ``status_code`` - checks that status code of the response is 2XX
- ``response_url`` - check if there is not redirect and the response is 2XX

See the details of check mechanisms in the `checking.py <https://github.com/soxoj/maigret/blob/main/maigret/checking.py#L339>`_ file.

Testing
-------

It is recommended use Python 3.10 for testing.

Install test requirements:

.. code-block:: console

  poetry install --with dev


Use the following commands to check Maigret:

.. code-block:: console

  # run linter and typing checks
  # order of checks:
  # - critical syntax errors or undefined names
  # - flake checks
  # - mypy checks
  make lint

  # run black formatter
  make format

  # run testing with coverage html report
  # current test coverage is 58%
  make test

  # open html report
  open htmlcov/index.html

  # get flamechart of imports to estimate startup time
  make speed


How to fix false-positives
-----------------------------------------------

If you want to work with sites database, don't forget to activate statistics update git hook, command for it would look like this: ``git config --local core.hooksPath .githooks/``.

You should make your git commits from your maigret git repo folder, or else the hook wouldn't find the statistics update script.

1. Determine the problematic site.

If you already know which site has a false-positive and want to fix it specifically, go to the next step.

Otherwise, simply run a search with a random username (e.g. `laiuhi3h4gi3u4hgt`) and check the results.
Alternatively, you can use `the Telegram bot <https://t.me/osint_maigret_bot>`_.

2. Open the account link in your browser and check:

- If the site is completely gone, remove it from the list
- If the site still works but looks different, update in data.json how we check it
- If the site requires login to view profiles, disable checking it

3. Find the site in the `data.json <https://github.com/soxoj/maigret/blob/main/maigret/resources/data.json>`_ file.

If the ``checkType`` method is not ``message`` and you are going to fix check, update it:
- put ``message`` in ``checkType``
- put in ``absenceStrs`` a keyword that is present in the HTML response for an non-existing account
- put in ``presenceStrs`` a keyword that is present in the HTML response for an existing account

If you have trouble determining the right keywords, you can use automatic detection by passing the account URL with the ``--submit`` option:

.. code-block:: console

  maigret --submit https://my.mail.ru/bk/alex

To disable checking, set ``disabled`` to ``true`` or simply run:

.. code-block:: console

  maigret --self-check --site My.Mail.ru@bk.ru

To debug the check method using the response HTML, you can run:

.. code-block:: console

  maigret soxoj --site My.Mail.ru@bk.ru -d 2> response.txt

There are few options for sites data.json helpful in various cases:

- ``engine`` - a predefined check for the sites of certain type (e.g. forums), see the ``engines`` section in the JSON file
- ``headers`` - a dictionary of additional headers to be sent to the site
- ``requestHeadOnly`` - set to ``true`` if it's enough to make a HEAD request to the site
- ``regexCheck`` - a regex to check if the username is valid, in case of frequent false-positives

.. _activation-mechanism:

Activation mechanism
--------------------

The activation mechanism helps make requests to sites requiring additional authentication like cookies, JWT tokens, or custom headers.

Let's study the Vimeo site check record from the Maigret database:

.. code-block:: json

      "Vimeo": {
          "tags": [
              "us",
              "video"
          ],
          "headers": {
              "Authorization": "jwt eyJ0..."
          },
          "activation": {
              "url": "https://vimeo.com/_rv/viewer",
              "marks": [
                  "Something strange occurred. Please get in touch with the app's creator."
              ],
              "method": "vimeo"
          },
          "urlProbe": "https://api.vimeo.com/users/{username}?fields=name...",
          "checkType": "status_code",
          "alexaRank": 148,
          "urlMain": "https://vimeo.com/",
          "url": "https://vimeo.com/{username}",
          "usernameClaimed": "blue",
          "usernameUnclaimed": "noonewouldeverusethis7"
      },

The activation method is:

.. code-block:: python

    def vimeo(site, logger, cookies={}):
        headers = dict(site.headers)
        if "Authorization" in headers:
            del headers["Authorization"]
        import requests

        r = requests.get(site.activation["url"], headers=headers)
        jwt_token = r.json()["jwt"]
        site.headers["Authorization"] = "jwt " + jwt_token

Here's how the activation process works when a JWT token becomes invalid:

1. The site check makes an HTTP request to ``urlProbe`` with the invalid token
2. The response contains an error message specified in the ``activation``/``marks`` field
3. When this error is detected, the ``vimeo`` activation function is triggered
4. The activation function obtains a new JWT token and updates it in the site check record
5. On the next site check (either through retry or a new Maigret run), the valid token is used and the check succeeds

Examples of activation mechanism implementation are available in `activation.py <https://github.com/soxoj/maigret/blob/main/maigret/activation.py>`_ file.

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

Documentation updates
---------------------

Documentations is auto-generated and auto-deployed from the ``docs`` directory.

To manually update documentation:

1. Change something in the ``.rst`` files in the ``docs/source`` directory.
2. Install ``pip install -r requirements.txt`` in the docs directory.
3. Run ``make singlehtml`` in the terminal in the docs directory.
4. Open ``build/singlehtml/index.html`` in your browser to see the result.
5. If everything is ok, commit and push your changes to GitHub. 

Roadmap
-------

.. warning::
   This roadmap requires updating to reflect the current project status and future plans.

.. figure:: https://i.imgur.com/kk8cFdR.png   
   :target: https://i.imgur.com/kk8cFdR.png
   :align: center
