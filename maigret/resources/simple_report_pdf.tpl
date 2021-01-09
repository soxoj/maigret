<html>
<head>
    <meta charset="utf-8" />
</head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, shrink-to-fit=no" />
<title>{{ username }} -- Maigret username search report</title>
<style>
    .table td, .table th {
        padding: .4rem;
    }
    @media print {
        .pagebreak { page-break-before: always; }
    }
</style>
<body>
    <div class="container">
        <div class="row-mb">
            <div class="col-12 card-body" style="padding-bottom: 0.5rem; width:100%">
                <h2 class="mb-0">
                    Username search report for {{ username }}
                </h2>
                <small>Generated at {{ generated_at }}</small>
            </div>
        </div>
        <div class="">
                <div class="">
                    <div class="">
                        <div class="">
                            <h3>Supposed personal data</h3>
                            {% for k, v in supposed_data.items() %}
                            <span>
                                {{ k }}: {{ v }}
                            </span>
                            {% endfor %}
                            {% if countries_tuple_list %}
                            <span>
                                Geo: {% for k, v in countries_tuple_list %}{{ k }} <span class="text-muted">({{ v }})</span>{{ ", " if not loop.last }}{% endfor %}
                            </span>
                            {% endif %}{% if interests_tuple_list %}
                            <span>
                                Interests: {% for k, v in interests_tuple_list %}{{ k }} <span class="text-muted">({{ v }})</span>{{ ", " if not loop.last }}{% endfor %}
                            </span>
                            {% endif %}{% if first_seen %}
                            <span>
                                First seen: {{ first_seen }}
                            </span>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            <div class="">
                <div class="">
                    <div class="">
                        <div class="">
                            <h3>Brief</h3>
                            <span>
                                {{ brief }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            {% for u, t, data in results %}
                {% for k, v in data.items() %}
                    {% if v.found and not v.is_similar %}
            <div style="clear:both;width:100%;"></div>
            <div class="" style="margin-top:20px;padding-top:10px;border-top: 1px solid #ccc;">
                <div class="">
                    <div class="">
                        <img class="" alt="Photo" style="width: 200px; height: 200px; object-fit: scale-down;float:left;" src="{{ v.status.ids_data.image or 'https://i.imgur.com/040fmbw.png' }}" data-holder-rendered="true">
                        <div class="" style="padding-top: 0;float:left;margin-left:50px;">
                        <h3 class="">
                            <a class="text-dark" href="{{ v.url_main }}" target="_blank">{{ k }}</a>
                        </h3>
                        {% if v.status.tags %}
                            <div class="mb-1 text-muted">Tags: {{ v.status.tags | join(', ') }}</div>
                        {% endif %}
                        <p class="card-text">
                            <a href="{{ v.url_user }}" target="_blank">{{ v.url_user }}</a>
                        </p>
                        {% if v.ids_data %}
                        </div>
                        <div style="clear:both;"></div>
                        <div style="width:100%">
                        <p style="background-color:#B7B7B7" ><h4>Details</h4></p>
                        <table class="table table-striped;" style="margin-top:5px;">
                            <tbody>
                            {% for k1, v1 in v.ids_data.items() %}
                                {% if k1 != 'image' %}
                                <tr>
                                    <th style="width:100px;">{{ title(k1) }}</th>
                                    <td>{% if v1 is iterable and (v1 is not string and v1 is not mapping) %}{{ v1 | join(', ') }}{% else %}{{ detect_link(v1) }}{% endif %}</td>
                                </tr>
                                {% endif %}

                            {% endfor %}
                            </tbody>
                        </table>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
                    {% endif %}
                {% endfor %}
            {% endfor %}
    </div>
</body>
</html>