from form_designer import settings as app_settings
from form_designer.forms import DesignedForm
from form_designer.models import FormDefinition
from form_designer.uploads import handle_uploaded_files

from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.core.context_processors import csrf
from django.utils.translation import ugettext as _


def process_form(request, form_definition, extra_context={},
        disable_redirection=False, suppress_messages=False,
        force_log_data=False, force_retain=False, suppress_log_data=False):

    context = extra_context
    success_message = form_definition.success_message or _('Thank you, the data was submitted successfully.')
    error_message = form_definition.error_message or _('The data could not be submitted, please try again.')
    form_error = False
    form_success = False
    is_submit = False
    # If the form has been submitted...
    if request.method == 'POST' and request.POST.get(form_definition.submit_flag_name):
        form = DesignedForm(form_definition, None, request.POST, request.FILES)
        is_submit = True
    if request.method == 'GET' and request.GET.get(form_definition.submit_flag_name):
        form = DesignedForm(form_definition, None, request.GET)
        is_submit = True

    if is_submit:
        if form.is_valid():
            # Handle file uploads using storage object
            files = handle_uploaded_files(form_definition, form)

            # Successful submission
            if not suppress_messages:
                messages.success(request, success_message)
            form_success = True
            if not suppress_log_data \
                and (form_definition.log_data or force_log_data):
                    context["form_log"] = form_definition.log(form, request.user)
            if form_definition.mail_to:
                form_definition.send_mail(form, files)
            if form_definition.success_redirect and not disable_redirection:
                return HttpResponseRedirect(form_definition.action or '?')
            if form_definition.success_clear and not force_retain:
                form = DesignedForm(form_definition) # clear form
        else:
            form_error = True
            if not suppress_messages:
                messages.error(request, error_message)
    else:
        if form_definition.allow_get_initial:
            form = DesignedForm(form_definition, initial_data=request.GET)
        else:
            form = DesignedForm(form_definition)

    context.update({
        'form_error': form_error,
        'form_success': form_success,
        'form': form,
        'form_definition': form_definition
    })
    context.update(csrf(request))

    if form_definition.display_logged:
        logs = form_definition.logs.all().order_by('created')
        context.update({'logs': logs})

    return context

def _form_detail_view(request, form_definition):
    result = process_form(request, form_definition)
    if isinstance(result, HttpResponseRedirect):
        return result
    result.update({
        'form_template': form_definition.form_template_name or app_settings.DEFAULT_FORM_TEMPLATE
    })
    return render_to_response('html/formdefinition/detail.html', result,
        context_instance=RequestContext(request))

def detail(request, object_name):
    form_definition = get_object_or_404(FormDefinition, name=object_name, require_hash=False)
    return _form_detail_view(request, form_definition)

def detail_by_hash(request, public_hash):
    form_definition = get_object_or_404(FormDefinition, public_hash=public_hash)
    return _form_detail_view(request, form_definition)
