from django.shortcuts import render


def home_view(request):
    """Главная страница: hero-блок и список услуг."""
    return render(request, 'core/home.html')


def services_view(request):
    """Страница «Наши услуги»."""
    return render(request, 'core/services.html')


def portfolio_view(request):
    """Страница «Наши работы» (портфолио)."""
    return render(request, 'core/portfolio.html')


def contacts_view(request):
    """Страница «Контакты» с формой заявки на расчёт."""
    return render(request, 'core/contacts.html')


def cabinet_view(request):
    """Личный кабинет — рендерится шаблон, данные грузятся через API."""
    return render(request, 'core/cabinet.html')


def admin_panel_view(request):
    """Панель администратора — управление заявками и статистика."""
    return render(request, 'core/admin_panel.html')
