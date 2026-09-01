$(function() {
    // Обновление UI при изменении auth
    function updateAuthUI() {
        const user = API.user;
        if (user) {
            $('.js-guest-only').addClass('hidden');
            $('.js-auth-only').removeClass('hidden');
            $('.js-user-name').text(user.first_name || user.username);
            $('.js-user-initials').text(user.initials);
            $('.js-user-role').text(user.role === 'master' ? 'Мастер' : 'Клиент');
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
            showToast('Добро пожаловать, ' + res.user.first_name + '!');
            window.location.href = '/';
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
            showToast('С возвращением, ' + res.user.first_name + '!');
            window.location.href = '/';
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