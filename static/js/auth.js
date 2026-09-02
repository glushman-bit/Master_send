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
        if (user) {
            $('.js-guest-only').addClass('hidden');
            $('.js-auth-only').removeClass('hidden');
            $('.js-user-name').text(user.first_name || user.username);
            $('.js-user-initials').text(user.initials);
            $('.js-user-role').text(user.role === 'master' ? 'Мастер' : 'Клиент');
            if (user.avatar) {
                $('.user-chip .user-avatar').html(`<img class="mini-avatar" src="${user.avatar}" alt="">`);
            } else {
                $('.user-chip .user-avatar').text(user.initials);
            }
        } else {
            $('.js-guest-only').removeClass('hidden');
            $('.js-auth-only').addClass('hidden');
        }
    }
    $(document).on('auth:change', updateAuthUI);
    updateAuthUI();

    // Форма регистрации
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
            API.setAuth(res.tokens, res.user);
            closeAuthModal();
            showToast('Добро пожаловать, ' + (res.user.first_name || res.user.username) + '!');
        } catch (err) {
            const msg = extractError(err);
            $err.text(msg).removeClass('hidden');
        } finally {
            $btn.prop('disabled', false).text('Зарегистрироваться');
        }
    });

    // Форма входа
    $(document).on('submit', '#loginForm', async function(e) {
        e.preventDefault();
        const $form = $(this);
        const $btn = $form.find('button[type=submit]');
        const $err = $form.find('.js-error');
        $err.text('').addClass('hidden');
        $btn.prop('disabled', true).text('Вход...');

        const data = Object.fromEntries(new FormData(this));
        try {
            const res = await API.post('/auth/login/', data);
            API.setAuth(res.tokens, res.user);
            closeAuthModal();
            showToast('С возвращением, ' + (res.user.first_name || res.user.username) + '!');
        } catch (err) {
            $err.text(extractError(err)).removeClass('hidden');
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