$(function() {
    // ===== Модальное окно входа / регистрации =====
    function openAuthModal(mode) {
        $('#authModal').removeClass('hidden');
        $('body').addClass('modal-open');
        showAuthMode(mode || 'login');
        setTimeout(() => $('#authModal .form-input:visible').first().focus(), 50);
    }

    function closeAuthModal() {
        $('#authModal').addClass('hidden');
        $('body').removeClass('modal-open');
        $('.js-error', '#authModal').text('').addClass('hidden');
        $('#authModal form').each(function() { this.reset(); });
    }

    function showAuthMode(mode) {
        const isLogin = mode === 'login';
        $('#loginForm').toggleClass('hidden', !isLogin);
        $('#registerForm').toggleClass('hidden', isLogin);
        $('#registerSent').addClass('hidden');
        $('.js-resend-verify').addClass('hidden');
        $('.auth-tab').toggleClass('active', function() { return $(this).data('mode') === mode; });
        $('#authTitle').text(isLogin ? 'Вход' : 'Регистрация');
        $('#authSubtitle').text(isLogin ? 'Войдите в свой аккаунт' : 'Создайте новый аккаунт');
    }

    // Открытие по кнопкам
    $(document).on('click', '.js-open-login', function(e) {
        e.preventDefault();
        openAuthModal('login');
    });
    $(document).on('click', '.js-open-register', function(e) {
        e.preventDefault();
        openAuthModal('register');
    });

    // Переключение вкладок и ссылок
    $(document).on('click', '.auth-tab', function() {
        showAuthMode($(this).data('mode'));
    });
    $(document).on('click', '.js-to-register', function(e) {
        e.preventDefault(); showAuthMode('register');
    });
    $(document).on('click', '.js-to-login', function(e) {
        e.preventDefault(); showAuthMode('login');
    });

    // Закрытие: крестик, клик по фону, Esc
    $(document).on('click', '.js-auth-close', closeAuthModal);
    $(document).on('mousedown', '.modal-overlay', function(e) {
        if (e.target === this) closeAuthModal();
    });
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') closeAuthModal();
    });

    // Блокировка скролла фона при открытой модалке
    $(document).on('click', '.js-open-login, .js-open-register', function() {
        if (!$('#authModal').hasClass('hidden')) $('body').addClass('modal-open');
    });

    // Открытие по хэшу #login / #register
    if (location.hash === '#login') openAuthModal('login');
    else if (location.hash === '#register') openAuthModal('register');

    // Обновление UI при изменении auth
    function updateAuthUI() {
        const user = API.user;
        const isClient = !!user && !user.is_master;
        if (user) {
            $('.js-guest-only').addClass('hidden');
            $('.js-auth-only').removeClass('hidden');
            $('.js-user-name').text(user.first_name || user.username);
            $('.js-user-initials').text(user.initials);
            $('.js-user-role').text(user.is_master ? (user.role === 'master' ? 'Мастер' : 'Администратор') : 'Клиент');
            if (user.avatar) {
                $('.user-chip .user-avatar').html(`<img class="mini-avatar" src="${user.avatar}" alt="">`);
            } else {
                $('.user-chip .user-avatar').text(user.initials);
            }
            $('.js-admin-link').toggleClass('hidden', !user.is_master);
            $('.js-add-order-only').toggleClass('hidden', !!user.is_master);
            $('.js-order-blocked').toggleClass('hidden', isClient);
        } else {
            $('.js-guest-only').removeClass('hidden');
            $('.js-auth-only').addClass('hidden');
            $('.js-admin-link').addClass('hidden');
            $('.js-add-order-only').addClass('hidden');
            $('.js-order-blocked').removeClass('hidden');
        }
        $('.js-create-order').toggleClass('hidden', !!user && user.is_master);
    }

    // Кнопка «Создать заявку» в сайдбаре
    $(document).on('click', '.js-create-order', function(e) {
        e.preventDefault();
        const user = API.user;
        if (user && !user.is_master) {
            window.location.href = '/#order';
        } else {
            openWarningModal();
        }
    });

    // Модальное окно-предупреждение о необходимости авторизации
    function openWarningModal() {
        $('#warningModal').removeClass('hidden');
        $('body').addClass('modal-open');
    }
    function closeWarningModal() {
        $('#warningModal').addClass('hidden');
        $('body').removeClass('modal-open');
    }
    $(document).on('click', '.js-warning-close, .js-warning-login', function(e) {
        e.preventDefault(); closeWarningModal();
        if ($(this).hasClass('js-warning-login')) openAuthModal('login');
    });
    $(document).on('click', '.js-warning-register', function(e) {
        e.preventDefault(); closeWarningModal(); openAuthModal('register');
    });
    $(document).on('mousedown', '#warningModal', function(e) {
        if (e.target === this) closeWarningModal();
    });
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') closeWarningModal();
    });
    $(document).on('auth:change', updateAuthUI);
    updateAuthUI();

    // Переход со страницы подтверждения email: открываем окно входа/регистрации.
    const authRedirect = (function() {
        try { return JSON.parse(sessionStorage.getItem('mh_auth_redirect') || 'null'); }
        catch (e) { return null; }
    })();
    if (authRedirect) {
        try { sessionStorage.removeItem('mh_auth_redirect'); } catch (e) {}
        const mode = authRedirect.mode === 'register' ? 'register' : 'login';
        openAuthModal(mode);
        if (mode === 'login' && authRedirect.email) {
            setTimeout(() => {
                $('#loginUsername').val(authRedirect.email);
            }, 100);
        }
        if (authRedirect.toast) {
            setTimeout(() => showToast(authRedirect.toast, 'success'), 200);
        }
    }

    // Форма регистрации
    let lastRegisterEmail = '';

    $(document).on('submit', '#registerForm', async function(e) {
        e.preventDefault();
        const $form = $(this);
        const $btn = $form.find('button[type=submit]');
        const $err = $form.find('.js-error');
        $err.text('').addClass('hidden');
        $btn.prop('disabled', true).text('Регистрация...');

        const data = Object.fromEntries(new FormData(this));
        try {
            const res = await API.post('/auth/register/', data);
            lastRegisterEmail = (data.email || res.email || '').trim();
            showAuthSent(lastRegisterEmail);
        } catch (err) {
            const msg = extractError(err);
            $err.text(msg).removeClass('hidden');
        } finally {
            $btn.prop('disabled', false).text('Зарегистрироваться');
        }
    });

    function showAuthSent(email) {
        $('#loginForm, #registerForm, .auth-tabs').addClass('hidden');
        $('#registerSent').removeClass('hidden');
        $('#registerSentEmail').text(email || 'ваш email');
    }

    function hideAuthSent() {
        $('#registerSent').addClass('hidden');
        $('#authModal .js-error').text('').addClass('hidden');
        $('.js-resend-verify').addClass('hidden');
    }

    $(document).on('click', '.js-sent-to-login', function(e) {
        e.preventDefault();
        hideAuthSent();
        showAuthMode('login');
    });

    // Повторная отправка письма (с формы входа и с экрана «проверьте почту»)
    $(document).on('click', '.js-resend-register, .js-resend-login', async function() {
        const email = $(this).hasClass('js-resend-register')
            ? lastRegisterEmail
            : $('#loginUsername').val().trim();
        if (!email) {
            showToast('Укажите email для повторной отправки.', 'error');
            return;
        }
        const $btn = $(this);
        $btn.prop('disabled', true).text('Отправляем...');
        try {
            await API.post('/auth/resend-verification/', {email});
            showToast('Если такой email зарегистрирован, письмо отправлено.');
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            $btn.prop('disabled', false).text('Отправить письмо ещё раз');
        }
    });

    // Форма входа
    $(document).on('submit', '#loginForm', async function(e) {
        e.preventDefault();
        const $form = $(this);
        const $btn = $form.find('button[type=submit]');
        const $err = $form.find('.js-error');
        $err.text('').addClass('hidden');
        $('.js-resend-verify').addClass('hidden');
        $btn.prop('disabled', true).text('Вход...');

        const data = Object.fromEntries(new FormData(this));
        try {
            const res = await API.post('/auth/login/', data);
            API.setAuth(res.tokens, res.user);
            closeAuthModal();
            showToast('С возвращением, ' + (res.user.first_name || res.user.username) + '!');
        } catch (err) {
            $err.text(extractError(err)).removeClass('hidden');
            if (err.data && err.data.code === 'email_not_verified') {
                $('.js-resend-verify').removeClass('hidden');
            }
        } finally {
            $btn.prop('disabled', false).text('Войти');
        }
    });

    // Выход
    $(document).on('click', '.js-logout', async function() {
        try {
            if (API.tokens?.refresh) {
                await API.post('/auth/logout/', {refresh: API.tokens.refresh});
            }
        } catch (e) {}
        API.setAuth(null, null);
        showToast('Вы вышли из системы');
        window.location.href = '/';
    });

    // ===== Мобильное меню (бургер) =====
    function closeMobileMenu() {
        $('#siteHeader').removeClass('nav-open');
        $('.js-nav-burger').attr('aria-expanded', 'false');
        $('#mobileMenu').attr('aria-hidden', 'true');
    }

    $(document).on('click', '.js-nav-burger', function(e) {
        e.stopPropagation();
        const open = $('#siteHeader').hasClass('nav-open');
        $('#siteHeader').toggleClass('nav-open', !open);
        $(this).attr('aria-expanded', String(!open));
        $('#mobileMenu').attr('aria-hidden', String(open));
    });

    $(document).on('click', '.js-mobile-menu a', closeMobileMenu);

    $(document).on('click', function(e) {
        if ($('#siteHeader').hasClass('nav-open') && !$(e.target).closest('#siteHeader').length) {
            closeMobileMenu();
        }
    });

    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') closeMobileMenu();
    });

    window.addEventListener('resize', function() {
        if (window.innerWidth >= 901) closeMobileMenu();
    });

    function extractError(err) {
        if (err.data) {
            // DRF возвращает {field: [errors]}
            for (const key in err.data) {
                const val = err.data[key];
                if (Array.isArray(val)) return val[0];
                if (typeof val === 'string') return val;
            }
        }
        return err.message || 'Ошибка';
    }
});

function showToast(msg, type = 'success') {
    $('.toast').remove();
    const $t = $(`<div class="toast toast-${type}">${msg}</div>`);
    $('body').append($t);
    setTimeout(() => $t.fadeOut(300, () => $t.remove()), 3000);
}

function nlToP(text, cls) {
    if (!text) return '';
    const safe = String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    const clsAttr = cls ? ' class="' + cls + '"' : '';
    return safe
        .split(/\n\s*\n/)
        .filter(p => p.trim().length > 0)
        .map(p => '<p' + clsAttr + '>' + p.trim().split(/\n/).join('<br>') + '</p>')
        .join('');
}

function formatPhoneValue(value) {
    let d = String(value || '').replace(/\D/g, '');
    if (d.charAt(0) === '8' || d.charAt(0) === '7') d = d.slice(1);
    d = d.slice(0, 10);
    let out = '+7';
    if (d.length > 0) out += ' (' + d.slice(0, 3);
    if (d.length > 3) out += ') ' + d.slice(3, 6);
    if (d.length > 6) out += '-' + d.slice(6, 8);
    if (d.length > 8) out += '-' + d.slice(8, 10);
    return out;
}

function formatPhoneEl(el) {
    const val = el.value;
    const caret = typeof el.selectionStart === 'number' ? el.selectionStart : val.length;
    const digitsBefore = (val.slice(0, caret).match(/\d/g) || []).length;
    const out = formatPhoneValue(val);
    if (out === val) return;
    el.value = out;
    let pos = 0, n = 0;
    if (caret === val.length) {
        pos = out.length;
    } else {
        while (pos < out.length && n < digitsBefore) {
            if (/\d/.test(out.charAt(pos))) n++;
            pos++;
        }
    }
    if (el.setSelectionRange) {
        try { el.setSelectionRange(pos, pos); } catch (e) {}
    }
}

$(document).on('input', '.js-phone', function() { formatPhoneEl(this); });

$(document).on('click', '.js-order-ok', function() {
    const $card = $(this).closest('.order-form-card');
    $card.find('.order-success').addClass('hidden');
    $card.find('form').removeClass('hidden');
});