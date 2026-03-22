# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import migrations


# The default lent sheet template content, adapted from the original
# core/lentrecord/includes/lent_sheet.html and lent_checklist.html.
# Uses lending_profile instead of lending_configuration.
DEFAULT_LENT_SHEET_TEMPLATE = r"""{% extends "lending/printout_base.html" %}
{% load i18n markdown_extras %}

{% block extra_css %}
{% if lending_profile.lending_preparation_checklist %}
<style>
    .pagebreak { break-before: page; }
    .checklist { font-family: monospace; font-size: 9pt; }
    .admonition { background-color: #e6e6e6; margin: 1rem 0; padding: 1rem; box-shadow: 0 2px 4px 0 rgba(0,0,0,0.2); border-radius: .25rem; overflow: hidden; }
    .admonition.note { background-color: #ebf6eb; }
    .admonition-title { display: block; padding: .5rem 1rem; margin: -1rem; margin-bottom: 1rem; color: #fff; background-color: #313131; }
    .admonition.note .admonition-title { color: #fff; background-color: #5cb85c; }
</style>
{% endif %}
{% endblock %}

{% block sheet_content %}
<div style="display: flex; justify-content: space-between;">
    <div>
        <h2 style="margin-top: 0;">Geräte Verleih</h2>
        <p>Antrag auf Ausleihe eines IT-Geräts</p>
    </div>
    <div>
        <p>
            <strong style="padding: 0.2rem 0.5rem; border: 3px solid red; border-radius: 5px; color: white !important; background-color: red;">
                Ausfertigung für den/die Ausleiher/-in
            </strong>
        </p>
    </div>
</div>

<table>
    <thead>
        <tr><th colspan="2">I. Ausleihende</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Name:<br><i>(Name, Vorname)</i></th>
            <td>{{ record.person }}</td>
        </tr>
        <tr>
            <th>Abteilung/Forschungsgruppe:</th>
            <td>{{ record.person.organizational_unit.name }}</td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">II. IT Gerät</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Gerät</th>
            <td>
                <strong>
                    {% if record.device.manufacturer or record.device.series %}
                        {{ record.device.manufacturer }} {{ record.device.device_type }} {{ record.device.series }}
                        {% if record.device.serial_number %}({{ record.device.serial_number }}){% endif %}
                        <br>
                    {% endif %}
                    {{ record.device }}, Inventarnummer: {{ record.device.sap_id|default:'n/a' }}
                </strong>
                <br>
                <i style="font-size: smaller;">Tenant: {{ record.device.tenant }}</i>
            </td>
        </tr>
        <tr>
            <th>Sonstiges:<br><i>(Zubehör, Mängel, Zusätze)</i></th>
            <td>{{ record.lent_accessories|linebreaks }}</td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">III. Ausleihe</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Vereinbarte Ausleihfrist</th>
            <td>
                {% language 'de' %}
                    {{ record.lent_start_date }} {% if record.lent_desired_end_date %} – {{ record.lent_desired_end_date }}{% endif %}
                {% endlanguage %}
            </td>
        </tr>
        <tr>
            <td colspan="2">
                <p>
                    Ich bestätige, dass ich das Gerät in einwandfreiem Zustand am {% language 'de' %}{{ record.lent_start_date | date:"j. F Y" }}{% endlanguage %} erhalten habe. Ich werde das Gerät pfleglich und mit Sorgfalt behandeln. Ich bin darauf hingewiesen worden, dass ich bei Verlust oder Beschädigung regresspflichtig gemacht werden kann.
                    Diebstahl aus nicht gesicherten Bereichen, sowie Verletzungen der Sorgfaltspflicht bei Transport gelten als grob fahrlässig.
                </p>

                {% if lending_profile.mandatory_regulations.all %}
                    Ich bestätige, die folgenden Ordnungen zur Kenntnis genommen zu haben:
                    <ul>
                    {% for regulation in lending_profile.mandatory_regulations.all %}
                    <li style="margin-bottom: 0.5rem;">
                        ☑ {{ regulation.linktext }}
                        <br>
                        &lt;<a href="{{ regulation.display_url }}">{{ regulation.display_url }}</a>&gt;
                    </li>
                    {% endfor %}
                    </ul>
                {% endif %}

                <div class="confirmation">
                    <p>Freiburg, den {% language 'de' %}{% now "j. F Y" %}{% endlanguage %}</p>
                    <p class="signature">Unterschrift des Ausleihenden</p>
                </div>
            </td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">IV. Verleih-Bearbeitung <span>(EDV-Abteilung)</span></th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Bearbeitet:</th>
            <td>
                <table>
                    <tr>
                        <td>Name:</td>
                        <td></td>
                        <td>Datum: {% language 'de' %}{% now "SHORT_DATE_FORMAT" %}{% endlanguage %}</td>
                        <td></td>
                    </tr>
                </table>
            </td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">V. Rückgabe-Bearbeitung <span>(EDV-Abteilung)</span></th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Zurückerhalten:</th>
            <td>
                <table>
                    <tr>
                        <td>Name:</td>
                        <td></td>
                        <td>Datum:</td>
                        <td></td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <th>Zustand:</th>
            <td></td>
        </tr>
    </tbody>
</table>
{% endblock %}

{% block sheet_content_copy %}
<div
    class="pagebreak"
    style="display: flex; justify-content: space-between;"
>
    <div>
        <h2 style="margin-top: 0;">Geräte Verleih</h2>
        <p>Antrag auf Ausleihe eines IT-Geräts</p>
    </div>
    <div>
        <p>
            <strong style="padding: 0.2rem 0.5rem; border: 3px solid red; border-radius: 5px; color: white !important; background-color: red;">
                Ausfertigung für das Institut
            </strong>
        </p>
    </div>
</div>

<table>
    <thead>
        <tr><th colspan="2">I. Ausleihende</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Name:<br><i>(Name, Vorname)</i></th>
            <td>{{ record.person }}</td>
        </tr>
        <tr>
            <th>Abteilung/Forschungsgruppe:</th>
            <td>{{ record.person.organizational_unit.name }}</td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">II. IT Gerät</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Gerät</th>
            <td>
                <strong>
                    {% if record.device.manufacturer or record.device.series %}
                        {{ record.device.manufacturer }} {{ record.device.device_type }} {{ record.device.series }}
                        {% if record.device.serial_number %}({{ record.device.serial_number }}){% endif %}
                        <br>
                    {% endif %}
                    {{ record.device }}, Inventarnummer: {{ record.device.sap_id|default:'n/a' }}
                </strong>
                <br>
                <i style="font-size: smaller;">Tenant: {{ record.device.tenant }}</i>
            </td>
        </tr>
        <tr>
            <th>Sonstiges:<br><i>(Zubehör, Mängel, Zusätze)</i></th>
            <td>{{ record.lent_accessories|linebreaks }}</td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">III. Ausleihe</th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Vereinbarte Ausleihfrist</th>
            <td>
                {% language 'de' %}
                    {{ record.lent_start_date }} {% if record.lent_desired_end_date %} – {{ record.lent_desired_end_date }}{% endif %}
                {% endlanguage %}
            </td>
        </tr>
        <tr>
            <td colspan="2">
                <p>
                    Ich bestätige, dass ich das Gerät in einwandfreiem Zustand am {% language 'de' %}{{ record.lent_start_date | date:"j. F Y" }}{% endlanguage %} erhalten habe. Ich werde das Gerät pfleglich und mit Sorgfalt behandeln. Ich bin darauf hingewiesen worden, dass ich bei Verlust oder Beschädigung regresspflichtig gemacht werden kann.
                    Diebstahl aus nicht gesicherten Bereichen, sowie Verletzungen der Sorgfaltspflicht bei Transport gelten als grob fahrlässig.
                </p>

                {% if lending_profile.mandatory_regulations.all %}
                    Ich bestätige, die folgenden Ordnungen zur Kenntnis genommen zu haben:
                    <ul>
                    {% for regulation in lending_profile.mandatory_regulations.all %}
                    <li style="margin-bottom: 0.5rem;">
                        ☑ {{ regulation.linktext }}
                        <br>
                        &lt;<a href="{{ regulation.display_url }}">{{ regulation.display_url }}</a>&gt;
                    </li>
                    {% endfor %}
                    </ul>
                {% endif %}

                <div class="confirmation">
                    <p>Freiburg, den {% language 'de' %}{% now "j. F Y" %}{% endlanguage %}</p>
                    <p class="signature">Unterschrift des Ausleihenden</p>
                </div>
            </td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">IV. Verleih-Bearbeitung <span>(EDV-Abteilung)</span></th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Bearbeitet:</th>
            <td>
                <table>
                    <tr>
                        <td>Name:</td>
                        <td></td>
                        <td>Datum: {% language 'de' %}{% now "SHORT_DATE_FORMAT" %}{% endlanguage %}</td>
                        <td></td>
                    </tr>
                </table>
            </td>
        </tr>
    </tbody>
    <thead>
        <tr><th colspan="2">V. Rückgabe-Bearbeitung <span>(EDV-Abteilung)</span></th></tr>
    </thead>
    <tbody>
        <tr>
            <th>Zurückerhalten:</th>
            <td>
                <table>
                    <tr>
                        <td>Name:</td>
                        <td></td>
                        <td>Datum:</td>
                        <td></td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <th>Zustand:</th>
            <td></td>
        </tr>
    </tbody>
</table>
{% endblock %}

{% block checklist %}
{% if lending_profile.lending_preparation_checklist %}
<div class="pagebreak checklist">
    <h2>
        Checklist for
        EDV-ID: {{ record.device.edv_id|default:'n/a' }},
        SAP-ID: {{ record.device.sap_id|default:'n/a' }}
        <br>
        {{ record.device.manufacturer }} {{ record.device.series }}
        <br>
        for {{ record.person }}
    </h2>
    <hr>
    {{ lending_profile.lending_preparation_checklist | from_markdown | safe }}
    <hr>
</div>
{% endif %}
{% endblock %}
"""


def forward(apps, schema_editor):
    LendingConfiguration = apps.get_model("lending", "LendingConfiguration")
    LendingConfigurationRegulation = apps.get_model("lending", "LendingConfigurationRegulation")
    LendingProfile = apps.get_model("lending", "LendingProfile")
    LendingProfileRegulation = apps.get_model("lending", "LendingProfileRegulation")
    DeviceType = apps.get_model("core", "DeviceType")

    # Load existing global config
    try:
        config = LendingConfiguration.objects.get(pk=1)
        checklist_text = config.lending_preparation_checklist or ""
    except LendingConfiguration.DoesNotExist:
        config = None
        checklist_text = ""

    # Get existing regulations
    existing_regs = []
    if config:
        existing_regs = list(
            LendingConfigurationRegulation.objects.filter(
                lending_configuration=config
            ).values_list("regulation_id", "order")
        )

    # Create a LendingProfile for each non-deleted DeviceType
    for dt in DeviceType.objects.filter(deleted_at__isnull=True):
        profile = LendingProfile.objects.create(
            device_type=dt,
            lending_preparation_checklist=checklist_text,
            lent_sheet_template=DEFAULT_LENT_SHEET_TEMPLATE,
        )
        for reg_id, order in existing_regs:
            LendingProfileRegulation.objects.create(
                lending_profile=profile,
                regulation_id=reg_id,
                order=order,
            )


def backward(apps, schema_editor):
    # The schema rollback (0005 reverse) will drop the tables
    LendingProfile = apps.get_model("lending", "LendingProfile")
    LendingProfile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("lending", "0005_lendingprofile_lendingprofileregulation_and_more"),
        ("core", "0063_alter_lostrecord_options_alter_removedrecord_options"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
