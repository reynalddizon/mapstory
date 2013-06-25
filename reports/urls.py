from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template


urlpatterns = patterns(
    'mapstory.reports.views',

    url(r"^$",
        direct_to_template, {"template": "reports/build_reports.html"},
        name="reports_list"),

    url(r"generate-user-report",
        'generate_user_report',
        name="reports_user_report"),

    url(r"activity", "activity_report", name="reports_activity"),

)
