import ast
import csv
import io
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

import pycountry
import xmind
from dateutil.parser import parse as parse_datetime_str
from jinja2 import Template
from xhtml2pdf import pisa
from pyvis.network import Network
import networkx as nx

from .checking import SUPPORTED_IDS
from .result import QueryStatus
from .sites import MaigretDatabase
from .utils import is_country_tag, CaseConverter, enrich_link_str

SUPPORTED_JSON_REPORT_FORMATS = [
    "simple",
    "ndjson",
]

"""
UTILS
"""


def filter_supposed_data(data):
    # interesting fields
    allowed_fields = ["fullname", "gender", "location", "age"]
    filtered_supposed_data = {
        CaseConverter.snake_to_title(k): v[0]
        for k, v in data.items()
        if k in allowed_fields
    }
    return filtered_supposed_data


def sort_report_by_data_points(results):
    return dict(
        sorted(
            results.items(),
            key=lambda x: len(
                (x[1].get('status') and x[1]['status'].ids_data or {}).keys()
            ),
            reverse=True,
        )
    )


"""
REPORTS SAVING
"""


def save_csv_report(filename: str, username: str, results: dict):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        generate_csv_report(username, results, f)


def save_txt_report(filename: str, username: str, results: dict):
    with open(filename, "w", encoding="utf-8") as f:
        generate_txt_report(username, results, f)


def save_html_report(filename: str, context: dict):
    template, _ = generate_report_template(is_pdf=False)
    filled_template = template.render(**context)
    with open(filename, "w") as f:
        f.write(filled_template)


def save_pdf_report(filename: str, context: dict):
    template, css = generate_report_template(is_pdf=True)
    filled_template = template.render(**context)
    with open(filename, "w+b") as f:
        pisa.pisaDocument(io.StringIO(filled_template), dest=f, default_css=css)


def save_json_report(filename: str, username: str, results: dict, report_type: str):
    with open(filename, "w", encoding="utf-8") as f:
        generate_json_report(username, results, f, report_type=report_type)


class MaigretGraph:
    other_params = {'size': 10, 'group': 3}
    site_params = {'size': 15, 'group': 2}
    username_params = {'size': 20, 'group': 1}

    def __init__(self, graph):
        self.G = graph

    def add_node(self, key, value):
        node_name = f'{key}: {value}'

        params = self.other_params
        if key in SUPPORTED_IDS:
            params = self.username_params
        elif value.startswith('http'):
            params = self.site_params

        self.G.add_node(node_name, title=node_name, **params)

        if value != value.lower():
            normalized_node_name = self.add_node(key, value.lower())
            self.link(node_name, normalized_node_name)

        return node_name

    def link(self, node1_name, node2_name):
        self.G.add_edge(node1_name, node2_name, weight=2)


def save_graph_report(filename: str, username_results: list, db: MaigretDatabase):
    G = nx.Graph()
    graph = MaigretGraph(G)

    for username, id_type, results in username_results:
        username_node_name = graph.add_node(id_type, username)

        for website_name in results:
            dictionary = results[website_name]
            # TODO: fix no site data issue
            if not dictionary:
                continue

            if dictionary.get("is_similar"):
                continue

            status = dictionary.get("status")
            if not status:  # FIXME: currently in case of timeout
                continue

            if dictionary["status"].status != QueryStatus.CLAIMED:
                continue

            site_fallback_name = dictionary.get('url_user', f'{website_name}: {username.lower()}')
            # site_node_name = dictionary.get('url_user', f'{website_name}: {username.lower()}')
            site_node_name = graph.add_node('site', site_fallback_name)
            graph.link(username_node_name, site_node_name)

            def process_ids(parent_node, ids):
                for k, v in ids.items():
                    if k.endswith('_count') or k.startswith('is_') or k.endswith('_at'):
                        continue
                    if k in 'image':
                        continue

                    v_data = v
                    if v.startswith('['):
                        try:
                            v_data = ast.literal_eval(v)
                        except Exception as e:
                            logging.error(e)

                    # value is a list
                    if isinstance(v_data, list):
                        list_node_name = graph.add_node(k, site_fallback_name)
                        for vv in v_data:
                            data_node_name = graph.add_node(vv, site_fallback_name)
                            graph.link(list_node_name, data_node_name)

                            add_ids = {a: b for b, a in db.extract_ids_from_url(vv).items()}
                            if add_ids:
                                process_ids(data_node_name, add_ids)
                    else:
                    # value is just a string
                        # ids_data_name = f'{k}: {v}'
                        # if ids_data_name == parent_node:
                        #     continue

                        ids_data_name = graph.add_node(k, v)
                        # G.add_node(ids_data_name, size=10, title=ids_data_name, group=3)
                        graph.link(parent_node, ids_data_name)

                        # check for username
                        if 'username' in k or k in SUPPORTED_IDS:
                            new_username_node_name = graph.add_node('username', v)
                            graph.link(ids_data_name, new_username_node_name)

                        add_ids = {k: v for v, k in db.extract_ids_from_url(v).items()}
                        if add_ids:
                            process_ids(ids_data_name, add_ids)

            if status.ids_data:
                process_ids(site_node_name, status.ids_data)

    nodes_to_remove = []
    for node in G.nodes:
        if len(str(node)) > 100:
            nodes_to_remove.append(node)

    [G.remove_node(node) for node in nodes_to_remove]

    nt = Network(notebook=True, height="750px", width="100%")
    nt.from_nx(G)
    nt.show(filename)


def get_plaintext_report(context: dict) -> str:
    output = (context['brief'] + " ").replace('. ', '.\n')
    interests = list(map(lambda x: x[0], context.get('interests_tuple_list', [])))
    countries = list(map(lambda x: x[0], context.get('countries_tuple_list', [])))
    if countries:
        output += f'Countries: {", ".join(countries)}\n'
    if interests:
        output += f'Interests (tags): {", ".join(interests)}\n'
    return output.strip()


"""
REPORTS GENERATING
"""


def generate_report_template(is_pdf: bool):
    """
    HTML/PDF template generation
    """

    def get_resource_content(filename):
        return open(os.path.join(maigret_path, "resources", filename)).read()

    maigret_path = os.path.dirname(os.path.realpath(__file__))

    if is_pdf:
        template_content = get_resource_content("simple_report_pdf.tpl")
        css_content = get_resource_content("simple_report_pdf.css")
    else:
        template_content = get_resource_content("simple_report.tpl")
        css_content = None

    template = Template(template_content)
    template.globals["title"] = CaseConverter.snake_to_title  # type: ignore
    template.globals["detect_link"] = enrich_link_str  # type: ignore
    return template, css_content


def generate_report_context(username_results: list):
    brief_text = []
    usernames = {}
    extended_info_count = 0
    tags: Dict[str, int] = {}
    supposed_data: Dict[str, Any] = {}

    first_seen = None

    for username, id_type, results in username_results:
        found_accounts = 0
        new_ids = []
        usernames[username] = {"type": id_type}

        for website_name in results:
            dictionary = results[website_name]
            # TODO: fix no site data issue
            if not dictionary:
                continue

            if dictionary.get("is_similar"):
                continue

            status = dictionary.get("status")
            if not status:  # FIXME: currently in case of timeout
                continue

            if status.ids_data:
                dictionary["ids_data"] = status.ids_data
                extended_info_count += 1

                # detect first seen
                created_at = status.ids_data.get("created_at")
                if created_at:
                    if first_seen is None:
                        first_seen = created_at
                    else:
                        try:
                            known_time = parse_datetime_str(first_seen)
                            new_time = parse_datetime_str(created_at)
                            if new_time < known_time:
                                first_seen = created_at
                        except Exception as e:
                            logging.debug(
                                "Problems with converting datetime %s/%s: %s",
                                first_seen,
                                created_at,
                                str(e),
                            )

                for k, v in status.ids_data.items():
                    # suppose target data
                    field = "fullname" if k == "name" else k
                    if field not in supposed_data:
                        supposed_data[field] = []
                    supposed_data[field].append(v)
                    # suppose country
                    if k in ["country", "locale"]:
                        try:
                            if is_country_tag(k):
                                tag = pycountry.countries.get(alpha_2=v).alpha_2.lower()
                            else:
                                tag = pycountry.countries.search_fuzzy(v)[
                                    0
                                ].alpha_2.lower()
                            # TODO: move countries to another struct
                            tags[tag] = tags.get(tag, 0) + 1
                        except Exception as e:
                            logging.debug(
                                "Pycountry exception: %s", str(e), exc_info=True
                            )

            new_usernames = dictionary.get("ids_usernames")
            if new_usernames:
                for u, utype in new_usernames.items():
                    if u not in usernames:
                        new_ids.append((u, utype))
                        usernames[u] = {"type": utype}

            if status.status == QueryStatus.CLAIMED:
                found_accounts += 1
                dictionary["found"] = True
            else:
                continue

            # ignore non-exact search results
            if status.tags:
                for t in status.tags:
                    tags[t] = tags.get(t, 0) + 1

        brief_text.append(
            f"Search by {id_type} {username} returned {found_accounts} accounts."
        )

        if new_ids:
            ids_list = []
            for u, t in new_ids:
                ids_list.append(f"{u} ({t})" if t != "username" else u)
            brief_text.append("Found target's other IDs: " + ", ".join(ids_list) + ".")

    brief_text.append(f"Extended info extracted from {extended_info_count} accounts.")

    brief = " ".join(brief_text).strip()
    tuple_sort = lambda d: sorted(d, key=lambda x: x[1], reverse=True)

    if "global" in tags:
        # remove tag 'global' useless for country detection
        del tags["global"]

    first_username = username_results[0][0]
    countries_lists = list(filter(lambda x: is_country_tag(x[0]), tags.items()))
    interests_list = list(filter(lambda x: not is_country_tag(x[0]), tags.items()))

    filtered_supposed_data = filter_supposed_data(supposed_data)

    return {
        "username": first_username,
        # TODO: return brief list
        "brief": brief,
        "results": username_results,
        "first_seen": first_seen,
        "interests_tuple_list": tuple_sort(interests_list),
        "countries_tuple_list": tuple_sort(countries_lists),
        "supposed_data": filtered_supposed_data,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_csv_report(username: str, results: dict, csvfile):
    writer = csv.writer(csvfile)
    writer.writerow(
        ["username", "name", "url_main", "url_user", "exists", "http_status"]
    )
    for site in results:
        # TODO: fix the reason
        status = 'Unknown'
        if "status" in results[site]:
            status = str(results[site]["status"].status)
        writer.writerow(
            [
                username,
                site,
                results[site].get("url_main", ""),
                results[site].get("url_user", ""),
                status,
                results[site].get("http_status", 0),
            ]
        )


def generate_txt_report(username: str, results: dict, file):
    exists_counter = 0
    for website_name in results:
        dictionary = results[website_name]
        # TODO: fix no site data issue
        if not dictionary:
            continue
        if (
            dictionary.get("status")
            and dictionary["status"].status == QueryStatus.CLAIMED
        ):
            exists_counter += 1
            file.write(dictionary["url_user"] + "\n")
    file.write(f"Total Websites Username Detected On : {exists_counter}")


def generate_json_report(username: str, results: dict, file, report_type):
    is_report_per_line = report_type.startswith("ndjson")
    all_json = {}

    for sitename in results:
        site_result = results[sitename]
        # TODO: fix no site data issue
        if not site_result or not site_result.get("status"):
            continue

        if site_result["status"].status != QueryStatus.CLAIMED:
            continue

        data = dict(site_result)
        data["status"] = data["status"].json()
        data["site"] = data["site"].json
        for field in ["future", "checker"]:
            if field in data:
                del data[field]

        if is_report_per_line:
            data["sitename"] = sitename
            file.write(json.dumps(data) + "\n")
        else:
            all_json[sitename] = data

    if not is_report_per_line:
        file.write(json.dumps(all_json))


"""
XMIND 8 Functions
"""


def save_xmind_report(filename, username, results):
    if os.path.exists(filename):
        os.remove(filename)
    workbook = xmind.load(filename)
    sheet = workbook.getPrimarySheet()
    design_xmind_sheet(sheet, username, results)
    xmind.save(workbook, path=filename)


def add_xmind_subtopic(userlink, k, v, supposed_data):
    currentsublabel = userlink.addSubTopic()
    field = "fullname" if k == "name" else k
    if field not in supposed_data:
        supposed_data[field] = []
    supposed_data[field].append(v)
    currentsublabel.setTitle("%s: %s" % (k, v))


def design_xmind_sheet(sheet, username, results):
    alltags = {}
    supposed_data = {}

    sheet.setTitle("%s Analysis" % (username))
    root_topic1 = sheet.getRootTopic()
    root_topic1.setTitle("%s" % (username))

    undefinedsection = root_topic1.addSubTopic()
    undefinedsection.setTitle("Undefined")
    alltags["undefined"] = undefinedsection

    for website_name in results:
        dictionary = results[website_name]
        if not dictionary:
            continue
        result_status = dictionary.get("status")
        # TODO: fix the reason
        if not result_status or result_status.status != QueryStatus.CLAIMED:
            continue

        stripped_tags = list(map(lambda x: x.strip(), result_status.tags))
        normalized_tags = list(
            filter(lambda x: x and not is_country_tag(x), stripped_tags)
        )

        category = None
        for tag in normalized_tags:
            if tag in alltags.keys():
                continue
            tagsection = root_topic1.addSubTopic()
            tagsection.setTitle(tag)
            alltags[tag] = tagsection
            category = tag

        section = alltags[category] if category else undefinedsection
        userlink = section.addSubTopic()
        userlink.addLabel(result_status.site_url_user)

        ids_data = result_status.ids_data or {}
        for k, v in ids_data.items():
            # suppose target data
            if isinstance(v, list):
                for currentval in v:
                    add_xmind_subtopic(userlink, k, currentval, supposed_data)
            else:
                add_xmind_subtopic(userlink, k, v, supposed_data)

    # add supposed data
    filtered_supposed_data = filter_supposed_data(supposed_data)
    if len(filtered_supposed_data) > 0:
        undefinedsection = root_topic1.addSubTopic()
        undefinedsection.setTitle("SUPPOSED DATA")
        for k, v in filtered_supposed_data.items():
            currentsublabel = undefinedsection.addSubTopic()
            currentsublabel.setTitle("%s: %s" % (k, v))
