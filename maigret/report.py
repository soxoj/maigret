import ast
import csv
import io
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

import xmind  # type: ignore[import-untyped]
from dateutil.tz import gettz
from dateutil.parser import parse as parse_datetime_str
from jinja2 import Template

from .checking import SUPPORTED_IDS
from .result import MaigretCheckStatus
from .sites import MaigretDatabase
from .utils import is_country_tag, CaseConverter, enrich_link_str


ADDITIONAL_TZINFO = {"CDT": gettz("America/Chicago")}
SUPPORTED_JSON_REPORT_FORMATS = [
    "simple",
    "ndjson",
]

"""
UTILS
"""


def filter_supposed_data(data):
    allowed_fields = ["fullname", "gender", "location", "age"]

    def _first(v):
        if isinstance(v, (list, tuple)):
            return v[0] if v else ""
        return v

    return {
        CaseConverter.snake_to_title(k): _first(v)
        for k, v in data.items()
        if k in allowed_fields
    }


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
    with open(filename, "w", encoding="utf-8") as f:
        f.write(filled_template)


def save_pdf_report(filename: str, context: dict):
    template, css = generate_report_template(is_pdf=True)
    filled_template = template.render(**context)

    # moved here to speed up the launch of Maigret
    from xhtml2pdf import pisa  # type: ignore[import-untyped]

    with open(filename, "w+b") as f:
        pisa.pisaDocument(io.StringIO(filled_template), dest=f, default_css=css)


def save_json_report(filename: str, username: str, results: dict, report_type: str):
    with open(filename, "w", encoding="utf-8") as f:
        generate_json_report(username, results, f, report_type=report_type)


class MaigretGraph:
    other_params: dict = {'size': 10, 'group': 3}
    site_params: dict = {'size': 15, 'group': 2}
    username_params: dict = {'size': 20, 'group': 1}

    found_color = '#28a745'
    not_found_color = '#dc3545'
    site_color = '#17a2b8'
    account_color = '#ffc107'
    username_color = '#6f42c1'

    def __init__(self, graph):
        self.G = graph
        self.site_tags: Dict[str, list] = {}

    def add_node(self, key, value, color=None, tags=None, found=True):
        node_name = f'{key}: {value}'

        params = dict(self.other_params)
        if key in SUPPORTED_IDS:
            params = dict(self.username_params)
            color = color or self.username_color
        elif value.startswith('http'):
            params = dict(self.site_params)
            color = color or self.site_color

        if color:
            params['color'] = color

        title_parts = [f"Type: {key}", f"Value: {value}"]
        if tags:
            params['group'] = self._get_group_for_tags(tags)
            title_parts.append(f"Tags: {', '.join(tags[:3])}")
        title_parts.append(f"Found: {'Yes' if found else 'No'}")
        params['title'] = '\n'.join(title_parts)
        params['label'] = value[:25] + '...' if len(str(value)) > 25 else value

        self.G.add_node(node_name, **params)
        return node_name

    def _get_group_for_tags(self, tags):
        if not tags:
            return 3
        tag_lower = [t.lower() for t in tags]
        categories = {
            'social': [1, 'social', 'facebook', 'twitter', 'instagram', 'telegram', 'discord', 'reddit', 'linkedin'],
            'dev': [2, 'dev', 'github', 'gitlab', 'stackoverflow', 'code'],
            'music': [4, 'music', 'soundcloud', 'spotify', 'last.fm'],
            'gaming': [5, 'gaming', 'steam', 'twitch', 'xbox', 'playstation'],
            'Adult': [6, 'adult', 'nsfw'],
        }
        for cat_name, cat_data in categories.items():
            if any(t in cat_data[1:] for t in tag_lower):
                return cat_data[0]
        return 3

    def link(self, node1_name, node2_name, weight=None):
        if weight:
            self.G.add_edge(node1_name, node2_name, weight=weight)
        else:
            self.G.add_edge(node1_name, node2_name, weight=1)

    def link_related_by_tags(self, site1, site2):
        tags1 = self.site_tags.get(site1, [])
        tags2 = self.site_tags.get(site2, [])
        if tags1 and tags2:
            common = set(tags1) & set(tags2)
            if common:
                weight = len(common) * 2
                self.link(site1, site2, weight=weight)


def save_graph_report(filename: str, username_results: list, db: MaigretDatabase):
    import networkx as nx

    G: Any = nx.Graph()
    graph = MaigretGraph(G)

    base_site_nodes = {}
    site_account_nodes = {}
    processed_values: Dict[str, Any] = {}

    for username, id_type, results in username_results:
        norm_username = username.lower()
        username_node_name = graph.add_node(id_type, norm_username, found=True)

        for website_name, dictionary in results.items():
            if not dictionary or dictionary.get("is_similar"):
                continue

            status = dictionary.get("status")
            if not status or status.status != MaigretCheckStatus.CLAIMED:
                continue

            site_tags = status.tags if status else []
            site_base_url = website_name
            if site_base_url not in base_site_nodes:
                graph.site_tags[site_base_url] = site_tags
                base_site_nodes[site_base_url] = graph.add_node(
                    'site', site_base_url,
                    color=MaigretGraph.site_color,
                    tags=site_tags,
                    found=True
                )

            site_base_node_name = base_site_nodes[site_base_url]

            account_url = dictionary.get('url_user', f'{site_base_url}/{norm_username}')
            account_node_id = f"{site_base_url}: {account_url}"
            if account_node_id not in site_account_nodes:
                site_account_nodes[account_node_id] = graph.add_node(
                    'account', account_url,
                    color=MaigretGraph.account_color,
                    tags=site_tags,
                    found=True
                )

            account_node_name = site_account_nodes[account_node_id]

            graph.link(username_node_name, account_node_name, weight=3)
            graph.link(account_node_name, site_base_node_name, weight=3)

            def process_ids(parent_node, ids, source_site):
                for k, v in ids.items():
                    if (
                        k.endswith('_count')
                        or k.startswith('is_')
                        or k.endswith('_at')
                        or k in 'image'
                    ):
                        continue

                    norm_v = v.lower() if isinstance(v, str) else v
                    value_key = f"{k}:{norm_v}"

                    if value_key in processed_values:
                        ids_data_name = processed_values[value_key]
                    else:
                        v_data = v
                        if isinstance(v, str) and v.startswith('['):
                            try:
                                v_data = ast.literal_eval(v)
                            except Exception as e:
                                logging.error(e)
                                continue

                        if isinstance(v_data, list):
                            list_node_name = graph.add_node(k, source_site, tags=site_tags)
                            processed_values[value_key] = list_node_name
                            for vv in v_data:
                                data_node_name = graph.add_node(vv, source_site, tags=site_tags)
                                graph.link(list_node_name, data_node_name, weight=1)

                                add_ids = {
                                    a: b for b, a in db.extract_ids_from_url(vv).items()
                                }
                                if add_ids:
                                    process_ids(data_node_name, add_ids, source_site)
                            ids_data_name = list_node_name
                        else:
                            ids_data_name = graph.add_node(k, norm_v, tags=site_tags)
                            processed_values[value_key] = ids_data_name

                            if 'username' in k or k in SUPPORTED_IDS:
                                new_username_key = f"username:{norm_v}"
                                if new_username_key not in processed_values:
                                    new_username_node_name = graph.add_node(
                                        'username', norm_v,
                                        color=MaigretGraph.username_color,
                                        tags=site_tags,
                                        found=True
                                    )
                                    processed_values[new_username_key] = (
                                        new_username_node_name
                                    )
                                    graph.link(ids_data_name, new_username_node_name, weight=2)

                            add_ids = {
                                k: v for v, k in db.extract_ids_from_url(v).items()
                            }
                            if add_ids:
                                process_ids(ids_data_name, add_ids, source_site)

                    graph.link(parent_node, ids_data_name, weight=1)

            if status.ids_data:
                process_ids(account_node_name, status.ids_data, site_base_url)

    for site1 in base_site_nodes:
        for site2 in base_site_nodes:
            if site1 < site2:
                graph.link_related_by_tags(site1, site2)

    nodes_to_remove = [node for node in G.nodes if len(str(node)) > 100]
    G.remove_nodes_from(nodes_to_remove)

    single_degree_sites = [
        n for n, deg in G.degree() if n.startswith("site:") and deg <= 1
    ]
    G.remove_nodes_from(single_degree_sites)

    from pyvis.network import Network

    nt = Network(notebook=True, height="750px", width="100%")
    nt.from_nx(G)
    nt.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "font": {
          "size": 14,
          "face": "arial",
          "color": "#ffffff"
        },
        "borderWidth": 2,
        "shadow": true
      },
      "edges": {
        "color": {
          "inherit": "both"
        },
        "smooth": {
          "type": "continuous",
          "forceDirection": "none"
        },
        "shadow": true
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -30000,
          "centralGravity": 0.5,
          "springLength": 200,
          "springConstant": 0.04
        },
        "stabilization": {
          "iterations": 100
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      }
    }
    """)
    nt.options["nodes"]["color"] = {
        "background": "#4798d8",
        "border": "#2a6497",
        "highlight": {
          "background": "#ffeb3b",
          "border": "#ff9800"
        }
    }
    nt.options.groups = {
        1: {"color": {"background": MaigretGraph.username_color, "border": "#5a2d8c"}},
        2: {"color": {"background": MaigretGraph.site_color, "border": "#0d6e8c"}},
        3: {"color": {"background": "#6c757d", "border": "#545b63"}},
        4: {"color": {"background": "#e83e8c", "border": "#b02a69"}},
        5: {"color": {"background": "#20c997", "border": "#198a6d"}},
        6: {"color": {"background": "#fd7e14", "border": "#c96b00"}}
    }
    nt.show(filename)

    html_content = ""
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace(
        '<body>',
        '''<style>
        body { background-color: #1a1a2e; color: #e0e0e0; }
        #mynetwork { background-color: #16213e; border: 2px solid #0f3460; }
        </style>
        <body>'''
    )

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)


def get_plaintext_report(context: dict) -> str:
    output = (context['brief'] + " ").replace('. ', '.\n')
    interests = list(map(lambda x: x[0], context.get('interests_tuple_list', [])))
    countries = list(map(lambda x: x[0], context.get('countries_tuple_list', [])))
    if countries:
        output += f'Countries: {", ".join(countries)}\n'
    if interests:
        output += f'Interests (tags): {", ".join(interests)}\n'
    return output.strip()


def _md_format_value(value) -> str:
    """Format a value for Markdown output, detecting links."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    s = str(value)
    if s.startswith("http://") or s.startswith("https://"):
        return f"[{s}]({s})"
    return s


def generate_markdown_report(context: dict, run_info: dict = None) -> str:
    username = context.get("username", "unknown")
    generated_at = context.get("generated_at", "")
    brief = context.get("brief", "")
    countries = context.get("countries_tuple_list", [])
    interests = context.get("interests_tuple_list", [])
    first_seen = context.get("first_seen")
    results = context.get("results", [])

    # Collect ALL values for key fields across all accounts
    all_fields: Dict[str, list] = {}
    last_seen = None
    for _, _, data in results:
        for _, v in data.items():
            if not v.get("found") or v.get("is_similar"):
                continue
            ids_data = v.get("ids_data", {})
            # Map multiple source fields to unified output fields
            field_sources = {
                "fullname": ("fullname", "name"),
                "location": ("location", "country", "city", "country_code", "locale", "region"),
                "gender": ("gender",),
                "bio": ("bio", "about", "description"),
            }
            for out_field, source_keys in field_sources.items():
                for src in source_keys:
                    val = ids_data.get(src)
                    if val:
                        all_fields.setdefault(out_field, [])
                        val_str = str(val)
                        if val_str not in all_fields[out_field]:
                            all_fields[out_field].append(val_str)
            # Track last_seen
            for ts_field in ("last_online", "latest_activity_at", "updated_at"):
                ts = ids_data.get(ts_field)
                if ts and (last_seen is None or str(ts) > str(last_seen)):
                    last_seen = ts

    lines = []
    lines.append(f"# Report by searching on username \"{username}\"\n")

    # Generated line with run info
    gen_line = f"Generated at {generated_at} by [Maigret](https://github.com/soxoj/maigret)"
    if run_info:
        parts = []
        if run_info.get("sites_count"):
            parts.append(f"{run_info['sites_count']} sites checked")
        if run_info.get("flags"):
            parts.append(f"flags: `{run_info['flags']}`")
        if parts:
            gen_line += f" ({', '.join(parts)})"
    lines.append(f"{gen_line}\n")

    # Summary
    lines.append("## Summary\n")
    lines.append(f"{brief}\n")

    if all_fields:
        lines.append("**Information extracted from accounts:**\n")
        for field, values in all_fields.items():
            title = CaseConverter.snake_to_title(field)
            lines.append(f"- {title}: {'; '.join(values)}")
        lines.append("")

    if countries:
        geo = ", ".join(f"{code} (x{count})" for code, count in countries)
        lines.append(f"**Country tags:** {geo}\n")

    if interests:
        tags = ", ".join(f"{tag} (x{count})" for tag, count in interests)
        lines.append(f"**Website tags:** {tags}\n")

    if first_seen:
        lines.append(f"**First seen:** {first_seen}")
    if last_seen:
        lines.append(f"**Last seen:** {last_seen}")
    if first_seen or last_seen:
        lines.append("")

    # Accounts found
    lines.append("## Accounts found\n")

    for u, id_type, data in results:
        for site_name, v in data.items():
            if not v.get("found") or v.get("is_similar"):
                continue

            lines.append(f"### {site_name}\n")
            lines.append(f"- **URL:** [{v.get('url_user', '')}]({v.get('url_user', '')})")

            tags = v.get("status") and v["status"].tags or []
            if tags:
                lines.append(f"- **Tags:** {', '.join(tags)}")
                lines.append("")

            ids_data = v.get("ids_data", {})
            if ids_data:
                for field, value in ids_data.items():
                    if field == "image":
                        continue
                    title = CaseConverter.snake_to_title(field)
                    lines.append(f"- {title}: {_md_format_value(value)}")

            lines.append("")

    # Possible false positives
    lines.append("## Possible false positives\n")
    lines.append(
        f"This report was generated by searching for accounts matching the username `{username}`. "
        f"Accounts listed above may belong to different people who happen to use the same "
        f"or similar username. Results without extracted personal information could contain "
        f"some false positive findings. Always verify findings before drawing conclusions.\n"
    )

    # Ethical use
    lines.append("## Ethical use\n")
    lines.append(
        "This report is a result of a technical collection of publicly available information "
        "from online accounts and does not constitute personal data processing. If you intend "
        "to use this data for personal data processing or collection purposes, ensure your use "
        "complies with applicable laws and regulations in your jurisdiction (such as GDPR, "
        "CCPA, and similar).\n"
    )

    return "\n".join(lines)


def save_markdown_report(filename: str, context: dict, run_info: dict = None):
    content = generate_markdown_report(context, run_info)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


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

    # moved here to speed up the launch of Maigret
    import pycountry

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
                            known_time = parse_datetime_str(
                                first_seen, tzinfos=ADDITIONAL_TZINFO
                            )
                            new_time = parse_datetime_str(
                                created_at, tzinfos=ADDITIONAL_TZINFO
                            )
                            if new_time < known_time:
                                first_seen = created_at
                        except Exception as e:
                            logging.debug(
                                "Problems with converting datetime %s/%s: %s",
                                first_seen,
                                created_at,
                                str(e),
                                exc_info=True,
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
                                country = pycountry.countries.get(alpha_2=v)
                                tag = country.alpha_2.lower()  # type: ignore[union-attr]
                            else:
                                tag = pycountry.countries.search_fuzzy(v)[
                                    0
                                ].alpha_2.lower()  # type: ignore[attr-defined]
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

            if status.status == MaigretCheckStatus.CLAIMED:
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
            and dictionary["status"].status == MaigretCheckStatus.CLAIMED
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

        if site_result["status"].status != MaigretCheckStatus.CLAIMED:
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
    alltags: Dict[str, Any] = {}
    supposed_data: Dict[str, Any] = {}

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
        if not result_status or result_status.status != MaigretCheckStatus.CLAIMED:
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
