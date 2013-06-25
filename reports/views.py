from actstream.models import Action
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render_to_response
from mapstory.admin import export_via_model


@login_required
@user_passes_test(lambda u: u.is_superuser)
def generate_user_report(req):
    return export_via_model(
        User,
        req,
        User.objects.all(),
        exclude=[
            'password',
            'is_active',
            'is_superuser',
            'id'
        ]
    )

@login_required
@user_passes_test(lambda u: u.is_staff)
def activity_report(req):
    actions = Action.objects.all().order_by('-timestamp')
    page = int(req.GET.get('page', 0))
    size = 100
    count = actions.count()
    actions = actions[page * size: (page + 1) * size]
    next_page = page + 1 if count > page + 1 * size else 0
    return render_to_response('reports/activity.html', {'actions': actions, 'next_page': next_page})

