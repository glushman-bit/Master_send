$(function() {
    // ===== Индикатор новых заявок для администратора =====
    const BELL_POLL = 30000;
    let bellTimer = null;

    function updateBell() {
        const isAdmin = !!(API.user && API.user.is_master);
        $('.js-admin-bell').toggleClass('hidden', !isAdmin);
        if (!isAdmin) {
            clearInterval(bellTimer);
            bellTimer = null;
            return;
        }
        refreshBell();
        if (!bellTimer) bellTimer = setInterval(refreshBell, BELL_POLL);
    }

    async function refreshBell() {
        const $bell = $('.js-admin-bell');
        const $badge = $('#adminBellBadge');
        if (!$bell.length || $bell.hasClass('hidden')) return;
        try {
            const s = await API.get('/orders/stats/');
            if (s.new > 0) {
                $badge.text(s.new).removeClass('hidden');
                $bell.addClass('has-new');
            } else {
                $badge.addClass('hidden');
                $bell.removeClass('has-new');
            }
        } catch (e) {}
    }

    $(document).on('auth:change', updateBell);
    updateBell();
});