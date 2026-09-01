from django.shortcuts import render


def home_view(request):
    return render(request, 'core/home.html')


def services_view(request):
    return render(request, 'core/services.html')


def portfolio_view(request):
    return render(request, 'core/portfolio.html')


def contacts_view(request):
    return render(request, 'core/contacts.html')


def cabinet_view(request):
    """Личный кабинет — рендерится шаблон, данные грузятся через API."""
    return render(request, 'core/cabinet.html')
