from .models import Interface


def interface_processor(request):
    setting = Interface.get_interface_setting()
    context = {'INTERFACE': setting}
    return context

