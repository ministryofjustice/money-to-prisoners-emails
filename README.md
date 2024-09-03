# Emails – Prisoner Money

Application to handle emails links to download files and GOV.UK Notify callbacks.

## Why this application exists

### Email links
We’re adopting GOV.UK Notify to send emails. Unfortunately it has some limitations:
- it doesn’t allow attachments, emails contains a link to download the files instead
- only certain file types are allowed (e.g. no ZIP files)
- the service sometimes rejects some Excel files (`.xlsx`) which should be accepted
  (Excel files are a bunch of files in a ZIP archive, so yes, technically they are ZIP files)
- it doesn’t give us any control over the downloaded file’s filename, MIME type or even extension

Especially this last limitation could be a problem not only from a UX perspective but also because
some of the files we email are uploaded to 3rd party systems. These could use filenames to determine
things like prison or date without asking for user input.

### GOV.UK Notify callbacks
The other responsibility for this application is to handle the GOV.UK Notify callbacks to keep track
of sent emails’ statuses, bounced email addresses, etc...

There are no other obvious places for this functionality to live in - aside from possibly `api` which
is not accessible from the internet - therefore have it in this separate application seemed logical.

## Requirements

- Unix-like platform with Python 3.12 and NodeJS 20 (e.g. via [nvm](https://github.com/nvm-sh/nvm#installing-and-updating) or [fnm](https://github.com/Schniz/fnm#installation))

## Running locally

It’s recommended that you use a python virtual environment to isolate each application.

The simplest way to do this is using:

```shell
python3 -m venv venv    # creates a virtual environment for dependencies; only needed the first time
. venv/bin/activate     # activates the virtual environment; needed every time you use this app
```

Some build tasks expect the active virtual environment to be at `/venv/`, but should generally work regardless of
its location.

You can copy `mtp_emails/settings/local.py.sample` to `local.py` to overlay local settings that won’t be committed,
but it’s not required for a standard setup.

To run the application locally, run:

```shell
./run.py serve
# or
./run.py start
```

This will build everything and run the local server at [http://localhost:8006/](http://localhost:8006/).
The former also starts browser-sync at [http://localhost:3006/](http://localhost:3006/).

All build/development actions can be listed with `./run.py --verbosity 2 help`.

### Alternative: Docker

In order to run a server that’s exactly similar to the production machines,
you need to have [Docker](https://www.docker.com/products/developer-tools) installed. Run

```shell
./run.py local_docker
```

and you should be able to connect to the local server.

## Developing

[![CircleCI](https://circleci.com/gh/ministryofjustice/money-to-prisoners-emails.svg?style=svg)](https://circleci.com/gh/ministryofjustice/money-to-prisoners-emails)

With the `./run.py` command, you can run a browser-sync server, and get the assets
to automatically recompile when changes are made, run `./run.py serve` instead of
`./run.py start`. The server is then available at the URL indicated.

```shell
./run.py test
```

Runs all the application tests.

You can connect a local version of [money-to-prisoners-common](https://github.com/ministryofjustice/money-to-prisoners-common/)
for development by pre-pending the following task to the run script.

```shell
python_dependencies --common-path [path]
```

### Translating

Update translation files with `./run.py make_messages` – you need to do this every time any translatable text is updated.

Requires [transifex cli tool](https://github.com/transifex/cli#installation) for synchronisation:

Pull updates from Transifex with `./run.py translations --pull`.
You’ll need to update translation files afterwards and manually check that the merges occurred correctly.

Push latest English to Transifex with `./run.py translations --push`.
NB: you should pull updates before pushing to merge correctly.

## Deploying

This is handled by [money-to-prisoners-deploy](https://github.com/ministryofjustice/money-to-prisoners-deploy/).
