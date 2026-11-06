#!/usr/bin/env python3
"""Detect site engines and update validated entries in a Maigret database."""

import asyncio
import copy
import json
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from alive_progress import alive_bar

# Support running the utility directly from a source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maigret.checking import SimpleAiohttpChecker, site_self_check  # noqa: E402
from maigret.sites import MaigretDatabase  # noqa: E402


async def check_engine_of_site(site, engine, semaphore, logger):
    """Return the site's name when its home page matches the engine markers."""
    markers = [marker for marker in getattr(engine, 'presenseStrs', []) if marker]
    if not markers:
        return None

    async with semaphore:
        checker = SimpleAiohttpChecker(logger=logger)
        try:
            checker.prepare(
                url=site.url_main,
                headers=site.headers,
                allow_redirects=True,
                timeout=10,
                encoding=site.encoding,
            )
            html_text, status_code, error = await checker.check()
            if (
                not error
                and 200 <= status_code < 300
                and html_text
                and all(marker in html_text for marker in markers)
            ):
                return site.name
        finally:
            await checker.close()
    return None


def _object_members(source, start):
    """Yield key and value spans from an already validated JSON object."""
    decoder = json.JSONDecoder()

    def skip_space(position):
        while source[position] in ' \t\r\n':
            position += 1
        return position

    position = skip_space(start + 1)
    while source[position] != '}':
        key_start = position
        key, position = decoder.raw_decode(source, position)
        position = skip_space(position)
        value_start = skip_space(position + 1)  # Skip the colon.
        _, value_end = decoder.raw_decode(source, value_start)
        yield key, key_start, value_start, value_end
        position = skip_space(value_end)
        if source[position] == '}':
            return
        position = skip_space(position + 1)  # Skip the comma.


def _save_site_updates(filename, source, updates):
    """Replace changed site values without rewriting other database entries."""
    if not updates:
        return

    root_start = len(source) - len(source.lstrip())
    sites_start = next(
        value_start
        for key, _, value_start, _ in _object_members(source, root_start)
        if key == 'sites'
    )
    replacements = []
    newline = '\r\n' if '\r\n' in source else '\n'
    for name, key_start, value_start, value_end in _object_members(source, sites_start):
        if name not in updates:
            continue
        line_start = source.rfind('\n', 0, key_start) + 1
        indent = source[line_start:key_start]
        if indent.strip():  # An entry on the same line as its parent object.
            indent = ''
        replacement = json.dumps(updates[name], indent=4, ensure_ascii=False)
        replacement = replacement.replace('\n', newline + indent)
        replacements.append((value_start, value_end, replacement))

    if len(replacements) != len(updates):
        raise ValueError('A detected site is missing from the database')
    updated = source
    for start, end, replacement in reversed(replacements):
        updated = updated[:start] + replacement + updated[end:]
    with open(filename, encoding='utf-8', newline='') as database_file:
        if database_file.read() != source:
            raise ValueError(
                'The database changed while checking engines; rerun the utility'
            )
    with open(filename, 'w', encoding='utf-8', newline='') as database_file:
        database_file.write(updated)


async def check_engines(
    base_file, engine_name=None, no_progressbar=False, max_connections=100
):
    logger = logging.getLogger('engines-check')
    with open(base_file, encoding='utf-8', newline='') as database_file:
        source = database_file.read()
    database_data = json.loads(source)
    db = MaigretDatabase().load_from_json(copy.deepcopy(database_data))
    sites = {site.name: site for site in db.sites}
    semaphore = asyncio.Semaphore(max_connections)
    updates = {}

    for engine in db.engines:
        if engine_name and engine.name != engine_name:
            continue
        if not any(getattr(engine, 'presenseStrs', [])):
            print(f'No features to automatically detect sites on engine {engine.name}')
            continue

        tasks = [
            asyncio.create_task(check_engine_of_site(site, engine, semaphore, logger))
            for site in sites.values()
            if not site.engine and not site.disabled
        ]
        detected_sites = []
        try:
            with alive_bar(
                len(tasks), title='Checking sites', disable=no_progressbar
            ) as progress:
                for task in asyncio.as_completed(tasks):
                    site_name = await task
                    if site_name is not None:
                        detected_sites.append(site_name)
                    progress()
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        print(f'Total detected {len(detected_sites)} sites on engine {engine.name}')
        updated_count = 0
        for site_name in detected_sites:
            candidate = copy.deepcopy(sites[site_name])
            candidate.engine = engine.name
            candidate.update_from_engine(engine)
            # Self-check can mutate both the candidate and its database, even on
            # failure. Keep those tentative changes out of the real database.
            result = await site_self_check(
                site=candidate,
                logger=logger,
                semaphore=semaphore,
                db=MaigretDatabase(),
                silent=True,
            )
            if result['disabled'] or result['issues'] or candidate.disabled:
                print(f'{site_name} failed username checking of engine {engine.name}')
                continue

            sites[site_name] = candidate
            db.update_site(candidate)
            # MaigretSite.json omits false/empty values, which could let engine
            # defaults replace explicit site settings after a database reload.
            updates[site_name] = copy.deepcopy(database_data['sites'][site_name])
            updates[site_name]['engine'] = engine.name
            if 'unchecked' in updates[site_name].get('tags', []):
                updates[site_name]['tags'].remove('unchecked')
            updated_count += 1
            print(f'Site "{site_name}": ' + json.dumps(updates[site_name], indent=4))

        print(f'Updated total {updated_count} sites!')

    _save_site_updates(base_file, source, updates)
    print('\nFinished checking site engines!')
    return len(updates)


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        '--base',
        '-b',
        dest='base_file',
        metavar='BASE_FILE',
        default='maigret/resources/data.json',
        help='JSON file with sites data to update.',
    )
    parser.add_argument('--engine', '-e', help='check only the selected engine')
    parser.add_argument(
        '--no-progressbar', action='store_true', help='disable progress output'
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        format='[%(filename)s:%(lineno)d] %(levelname)-3s  %(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        level=logging.INFO,
    )
    return asyncio.run(check_engines(args.base_file, args.engine, args.no_progressbar))


if __name__ == '__main__':
    main()
