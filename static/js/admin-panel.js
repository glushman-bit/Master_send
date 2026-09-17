$(function() {
    'use strict';

    const POLL_INTERVAL = 20000;
    let prevNew = null;
    let timer = null;

    function esc(s) {
        if (s === null || s === undefined) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function fmtDate(d) {
        if (!d) return '—';
        const dt = new Date(d);
        if (isNaN(dt)) return '—';
        return dt.toLocaleString('ru-RU', {day: '2-digit', month: '2-digit', year: 'numeric'});
    }

    function fmtDateTime(d) {
        if (!d) return '—';
        const dt = new Date(d);
        if (isNaN(dt)) return '—';
        return dt.toLocaleString('ru-RU');
    }

    function roleLabel(u) {
        if (u.is_superuser) return 'Администратор';
        return u.role === 'master' ? 'Мастер' : 'Клиент';
    }

    function isAdmin() {
        return !!(API.user && API.user.is_master);
    }

    if (!isAdmin()) {
        window.location.href = '/';
        return;
    }

    refreshAll();
    timer = setInterval(refreshAll, POLL_INTERVAL);

    async function refreshAll() {
        const filter = $('#adminStatusFilter').val() || 'new';
        await Promise.all([
            refreshStats(),
            refreshUserStats(),
            refreshOrders(filter),
            refreshUsers(),
            refreshWorks(),
            refreshServices(),
            refreshAbout(),
        ]);
    }

    /* ============ Статистика заявок ============ */
    async function refreshStats() {
        try {
            const s = await API.get('/orders/stats/');
            $('.js-stat-new').text(s.new);
            $('.js-stat-progress').text(s.in_progress);
            $('.js-stat-done').text(s.done);
            $('.js-stat-total').text(s.total);
            updateBadge(s.new);
            pulseIfNew(s.new);
        } catch (e) {}
    }

    async function refreshUserStats() {
        try {
            const s = await API.get('/auth/stats/');
            $('.js-users-total').text(s.total);
            $('.js-users-clients').text(s.clients);
            $('.js-users-masters').text(s.masters);
            $('.js-users-new-month').text(s.new_month);
            $('.js-users-active-week').text(s.active_week);
        } catch (e) {}
    }

    function updateBadge(count) {
        const $badge = $('#newOrdersBadge');
        if (count > 0) {
            $badge.text(count).removeClass('hidden');
        } else {
            $badge.addClass('hidden');
        }
    }

    function pulseIfNew(count) {
        if (prevNew === null) { prevNew = count; return; }
        if (count > prevNew) {
            $('#newOrdersBadge').addClass('pulse');
            showToast('Поступила новая заявка (' + count + ' новых)!', 'success');
            setTimeout(() => $('#newOrdersBadge').removeClass('pulse'), 2000);
        }
        prevNew = count;
    }

    /* ============ Заявки ============ */
    async function refreshOrders(status) {
        const url = status === 'all' ? '/orders/?page_size=1000' : '/orders/?status=' + status + '&page_size=1000';
        const $list = $('#adminOrdersList');
        try {
            const data = await API.get(url);
            const orders = data.results || data;
            if (!orders.length) {
                $list.html('<p class="muted">Заявок нет.</p>');
                return;
            }
            $list.html(orders.map(function(o) {
                let actions = '';
                if (o.status === 'new') {
                    actions =
                        '<button class="btn btn-sm btn-ghost js-set-status" data-id="' + o.id + '" data-status="progress">Взять в работу</button>' +
                        '<button class="btn btn-sm btn-ghost js-set-status" data-id="' + o.id + '" data-status="done">Выполнено</button>' +
                        '<button class="btn btn-sm btn-ghost js-set-status" data-id="' + o.id + '" data-status="cancelled">Отменить</button>';
                } else if (o.status === 'progress') {
                    actions =
                        '<button class="btn btn-sm btn-ghost js-set-status" data-id="' + o.id + '" data-status="done">Выполнено</button>' +
                        '<button class="btn btn-sm btn-ghost js-set-status" data-id="' + o.id + '" data-status="cancelled">Отменить</button>';
                } else {
                    actions = '<span class="muted">Заявка закрыта</span>';
                }
                return '<div class="order-item admin-order-item">' +
                    '<div class="admin-order-main">' +
                        '<strong>' + esc(o.name) + '</strong>' +
                        '<span class="status status-' + esc(o.status) + '">' + esc(o.status_display) + '</span>' +
                        '<span class="admin-order-created muted">📅 ' + fmtDateTime(o.created_at) + '</span>' +
                    '</div>' +
                    (o.user_name ? '<div class="muted">👤 ' + esc(o.user_name) + '</div>' : '') +
                    '<div class="muted">📞 ' + esc(o.phone || '—') + (o.email ? ' • ✉️ ' + esc(o.email) : '') + '</div>' +
                    '<div class="muted">' + esc(o.message) + '</div>' +
                    '<div class="admin-order-actions">' + actions + '</div>' +
                '</div>';
            }).join(''));
        } catch (e) {
            $list.html('<p class="muted">Не удалось загрузить заявки.</p>');
        }
    }

    $(document).on('click', '.js-set-status', async function() {
        const $btn = $(this);
        const id = $btn.data('id');
        const status = $btn.data('status');
        $btn.prop('disabled', true);
        try {
            await API.post('/orders/' + id + '/status/', {status: status});
            showToast('Статус заявки обновлён');
            refreshAll();
        } catch (err) {
            showToast(err.message || 'Не удалось обновить статус', 'error');
            $btn.prop('disabled', false);
        }
    });

    $('#adminStatusFilter').on('change', function() {
        refreshOrders(this.value);
    });

    /* ============ Модальное подтверждение ============ */
    let confirmCallback = null;

    function askConfirm(title, bodyHtml, okLabel, onConfirm) {
        $('#confirmModalTitle').text(title);
        $('#confirmModalBody').html(bodyHtml || '');
        $('#confirmModalOk').text(okLabel || 'Подтвердить');
        confirmCallback = onConfirm;
        $('#confirmModal').removeClass('hidden');
        $('body').addClass('modal-open');
    }

    function closeConfirm() {
        $('#confirmModal').addClass('hidden');
        confirmCallback = null;
        if ($('#workModal').hasClass('hidden') && $('#serviceModal').hasClass('hidden')) {
            $('body').removeClass('modal-open');
        }
    }

    $(document).on('click', '.js-confirm-cancel', closeConfirm);
    $(document).on('click', '.js-confirm-ok', function() {
        const cb = confirmCallback;
        closeConfirm();
        if (cb) cb();
    });

    /* ============ Пользователи ============ */
    function renderUserAvatar(u) {
        if (u.avatar) return '<img class="user-table-avatar" src="' + esc(u.avatar) + '" alt="">';
        return '<span class="user-table-avatar avatar-fallback">' + esc(u.initials) + '</span>';
    }

    function renderUserRow(u) {
        const isSelf = API.user && u.id === API.user.id;
        const isSuper = !!u.is_superuser;
        const statusClass = u.is_active ? 'status-active' : 'status-blocked';
        const statusText = u.is_active ? 'Активен' : 'Заблокирован';

        let actions;
        if (isSelf) {
            actions = '<span class="muted">Это вы</span>';
        } else if (isSuper) {
            actions = '<span class="muted">Администратор</span>';
        } else if (u.is_active) {
            actions = '<button class="btn btn-sm btn-danger js-block-user" data-id="' + u.id + '" data-block="1" data-name="' + esc(u.first_name || u.username) + '">Заблокировать</button>';
        } else {
            actions = '<button class="btn btn-sm btn-ghost js-block-user" data-id="' + u.id + '" data-block="0">Разблокировать</button>';
        }

        return '<tr class="' + (u.is_active ? '' : 'is-blocked') + '">' +
            '<td><div class="user-cell">' + renderUserAvatar(u) +
                '<div class="user-cell-info">' +
                    '<strong>' + esc(u.first_name || u.username) + '</strong>' +
                    '<div class="muted">@' + esc(u.username) + '</div>' +
                '</div>' +
            '</div></td>' +
            '<td><div class="muted">' + (u.email ? esc(u.email) : '—') + '</div>' +
                '<div class="muted">' + (u.phone ? esc(u.phone) : '—') + '</div></td>' +
            '<td class="cell-fit">' + esc((u.first_name || '') + ' ' + (u.last_name || '')).trim() + '</td>' +
            '<td class="cell-fit">' + esc(roleLabel(u)) + '</td>' +
            '<td class="t-total cell-fit"><strong>' + (u.orders ? u.orders.total : 0) + '</strong></td>' +
            '<td class="cell-fit muted">' + fmtDate(u.date_joined) + '</td>' +
            '<td class="cell-fit"><span class="status-badge ' + statusClass + '">' + statusText + '</span></td>' +
            '<td class="cell-fit">' + actions + '</td>' +
        '</tr>';
    }

    async function refreshUsers() {
        try {
            const users = await API.get('/auth/users/');
            const $list = $('#adminUsersList');
            if (!users || !users.length) {
                $list.html('<tr><td colspan="8" class="muted">Пользователей нет.</td></tr>');
                return;
            }
            $list.html(users.map(renderUserRow).join(''));
        } catch (e) {
            $('#adminUsersList').html('<tr><td colspan="8" class="muted">Не удалось загрузить.</td></tr>');
        }
    }

    $(document).on('click', '.js-block-user', function() {
        const $btn = $(this);
        const id = $btn.data('id');
        const block = $btn.data('block') === 1;
        const name = $btn.data('name') || '';

        async function applyStatus() {
            $btn.prop('disabled', true);
            try {
                const res = await API.post('/auth/users/' + id + '/block/', {is_active: !block});
                showToast(res.detail || 'Статус обновлён');
                refreshAll();
            } catch (err) {
                showToast(err.message || 'Не удалось изменить статус', 'error');
                $btn.prop('disabled', false);
            }
        }

        if (block) {
            askConfirm(
                'Заблокировать пользователя',
                '<p class="confirm-name">«' + esc(name) + '»</p>' +
                '<p class="muted">Пользователь не сможет войти на сайт и пользоваться личным кабинетом.</p>',
                'Заблокировать',
                applyStatus
            );
        } else {
            applyStatus();
        }
    });

    /* ============ Работы портфолио ============ */
    async function refreshWorks() {
        try {
            const data = await API.get('/admin/portfolio/?page_size=1000');
            const works = data.results || data;
            const $list = $('#adminWorksList');
            if (!works || !works.length) {
                $list.html('<tr><td colspan="6"><div class="admin-empty">Работ пока нет. Добавьте первую работу.</div></td></tr>');
                return;
            }
            $list.html(works.map(function(w) {
                const images = w.images || [];
                const cover = images.filter(i => i.kind === 'after')[0] || images[0];
                const thumb = cover
                    ? '<img class="admin-thumb" src="' + esc(cover.image) + '" alt="' + esc(w.title) + '">'
                    : '<span class="muted">—</span>';
                const before = images.filter(i => i.kind === 'before').length;
                const after = images.filter(i => i.kind === 'after').length;
                const pub = w.is_published
                    ? '<span class="status-badge status-active">Опубликована</span>'
                    : '<span class="status-badge status-blocked">Скрыта</span>';
                return '<tr>' +
                    '<td class="cell-fit">' + thumb + '</td>' +
                    '<td><strong>' + esc(w.title) + '</strong></td>' +
                    '<td>' + esc(w.service_title || '—') + '</td>' +
                    '<td class="cell-fit">' + before + ' / ' + after + '</td>' +
                    '<td class="cell-fit">' + pub + '</td>' +
                    '<td class="cell-fit"><div class="btn-row">' +
                        '<button class="btn btn-sm btn-ghost js-work-edit" data-id="' + w.id + '">Редактировать</button>' +
                        '<button class="btn btn-sm btn-danger js-work-delete" data-id="' + w.id + '">Удалить</button>' +
                    '</div></td>' +
                '</tr>';
            }).join(''));
        } catch (e) {
            $('#adminWorksList').html('<tr><td colspan="6" class="muted">Не удалось загрузить.</td></tr>');
        }
    }

    var workState = { images: [], removed: [], newFiles: { before: [], after: [] } };

    function renderWorkImages() {
        ['before', 'after'].forEach(function(kind) {
            const $list = kind === 'before' ? $('#workImgBeforeList') : $('#workImgAfterList');
            const items = [];
            workState.images.forEach(function(im) {
                if (im.kind !== kind || workState.removed.indexOf(im.id) !== -1) return;
                items.push('<div class="work-img-item">' +
                    '<img src="' + esc(im.image) + '" alt="">' +
                    '<button type="button" class="work-img-remove" data-kind="' + kind + '" data-old-id="' + im.id + '" aria-label="Удалить фото">&times;</button></div>');
            });
            workState.newFiles[kind].forEach(function(f, idx) {
                items.push('<div class="work-img-item work-img-new">' +
                    '<img src="' + URL.createObjectURL(f) + '" alt="">' +
                    '<button type="button" class="work-img-remove" data-kind="' + kind + '" data-new-idx="' + idx + '" aria-label="Удалить фото">&times;</button></div>');
            });
            $list.html(items.join(''));
        });
    }

    async function openWorkModal(work) {
        workState = { images: [], removed: [], newFiles: { before: [], after: [] } };
        // Заполняем select услуг
        try {
            const services = await API.get('/services/?page_size=1000');
            const list = services.results || services;
            const $sel = $('#workService');
            $sel.empty().append(list.map(s => '<option value="' + s.id + '">' + esc(s.title) + '</option>'));
        } catch (e) {}

        const $form = $('#workForm');
        $form.trigger('reset');
        $form.find('.js-work-error').text('').addClass('hidden');
        $('#workImgBefore').val('');
        $('#workImgAfter').val('');

        if (work) {
            $('#workModalTitle').text('Редактировать работу');
            $form.find('[name="id"]').val(work.id);
            $('#workTitle').val(work.title);
            $('#workService').val(work.service);
            $('#workDescription').val(work.description || '');
            $('#workPublished').prop('checked', !!work.is_published);
            workState.images = (work.images || []).map(function(im) {
                return { id: im.id, kind: im.kind, image: im.image };
            });
        } else {
            $('#workModalTitle').text('Новая работа');
            $form.find('[name="id"]').val('');
        }
        renderWorkImages();

        $('#workModal').removeClass('hidden');
        $('body').addClass('modal-open');
    }

    function closeWorkModal() {
        $('#workModal').addClass('hidden');
        $('body').removeClass('modal-open');
    }

    $(document).on('click', '.js-work-add', function() { openWorkModal(null); });
    $(document).on('click', '.js-work-edit', async function() {
        try {
            const work = await API.get('/admin/portfolio/' + $(this).data('id') + '/');
            openWorkModal(work);
        } catch (e) {
            showToast('Не удалось загрузить работу.', 'error');
        }
    });
    $(document).on('click', '.js-work-modal-close', closeWorkModal);

    $('#workImgBefore, #workImgAfter').on('change', function() {
        const kind = this.id === 'workImgBefore' ? 'before' : 'after';
        const files = Array.prototype.slice.call(this.files || []);
        if (files.length) {
            workState.newFiles[kind].push.apply(workState.newFiles[kind], files);
        }
        this.value = '';
        renderWorkImages();
    });

    $(document).on('click', '.work-img-remove', function() {
        const kind = $(this).data('kind');
        const oldId = $(this).data('old-id');
        if (oldId !== undefined) {
            workState.removed.push(oldId);
        } else {
            workState.newFiles[kind].splice($(this).data('new-idx'), 1);
        }
        renderWorkImages();
    });

    $('#workForm').on('submit', async function(e) {
        e.preventDefault();
        const $form = $(this);
        const id = $form.find('[name="id"]').val();
        const $btn = $form.find('button[type=submit]');
        const $err = $form.find('.js-work-error');
        $err.text('').addClass('hidden');

        const totalImages = workState.images.filter(im => workState.removed.indexOf(im.id) === -1).length
            + workState.newFiles.before.length + workState.newFiles.after.length;
        if (!id && !totalImages) {
            $err.text('Добавьте хотя бы одно фото («до» или «после»).').removeClass('hidden');
            return;
        }

        const data = new FormData();
        data.append('title', $('#workTitle').val());
        data.append('service', $('#workService').val());
        data.append('description', $('#workDescription').val() || '');
        data.append('is_published', $('#workPublished').is(':checked') ? 'true' : 'false');
        ['before', 'after'].forEach(function(kind) {
            workState.newFiles[kind].forEach(function(f) {
                data.append('images_' + kind, f, f.name);
            });
        });
        if (workState.removed.length) {
            data.append('remove_images', JSON.stringify(workState.removed));
        }

        $btn.prop('disabled', true).text('Сохранение...');
        try {
            if (id) {
                await API.patch('/admin/portfolio/' + id + '/', data, true);
                showToast('Работа обновлена');
            } else {
                await API.post('/admin/portfolio/', data, true);
                showToast('Работа добавлена');
            }
            closeWorkModal();
            refreshWorks();
        } catch (err) {
            let msg = err.message || 'Не удалось сохранить работу';
            if (err.data) {
                for (const key in err.data) {
                    const v = err.data[key];
                    if (Array.isArray(v)) { msg = v[0]; break; }
                    if (typeof v === 'string') { msg = v; break; }
                }
            }
            $err.text(msg).removeClass('hidden');
        } finally {
            $btn.prop('disabled', false).text('Сохранить работу');
        }
    });

    $(document).on('click', '.js-work-delete', function() {
        const $btn = $(this);
        const id = $btn.data('id');
        askConfirm(
            'Удалить работу?',
            '<p class="muted">Работа будет удалена безвозвратно вместе с файлами изображений.</p>',
            'Удалить',
            async function() {
                $btn.prop('disabled', true);
                try {
                    await API.delete('/admin/portfolio/' + id + '/');
                    showToast('Работа удалена');
                    refreshWorks();
                } catch (err) {
                    showToast(err.message || 'Не удалось удалить работу', 'error');
                    $btn.prop('disabled', false);
                }
            }
        );
    });

    /* ============ Услуги ============ */
    async function refreshServices() {
        try {
            const data = await API.get('/admin/services/?page_size=1000');
            const services = data.results || data;
            const $list = $('#adminServicesList');
            if (!services || !services.length) {
                $list.html('<tr><td colspan="8"><div class="admin-empty">Услуг пока нет.</div></td></tr>');
                return;
            }
            $list.html(services.map(function(s) {
                const active = s.is_active
                    ? '<span class="status-badge status-active">Активна</span>'
                    : '<span class="status-badge status-blocked">Неактивна</span>';
                return '<tr>' +
                    '<td class="cell-fit">' + esc(s.category_display) + '</td>' +
                    '<td><strong>' + esc(s.title) + '</strong></td>' +
                    '<td><div class="muted">' + esc(s.description) + '</div></td>' +
                    '<td class="cell-fit">от <strong>' + esc(s.price_from) + ' ₽</strong> ' + esc(s.price_unit) + '</td>' +
                    '<td class="cell-fit">' + esc(s.icon) + '</td>' +
                    '<td class="cell-fit">' + esc(s.order) + '</td>' +
                    '<td class="cell-fit">' + active + '</td>' +
                    '<td class="cell-fit"><div class="btn-row">' +
                        '<button class="btn btn-sm btn-ghost js-service-edit" data-id="' + s.id + '">Редактировать</button>' +
                        '<button class="btn btn-sm btn-danger js-service-delete" data-id="' + s.id + '">Удалить</button>' +
                    '</div></td>' +
                '</tr>';
            }).join(''));
        } catch (e) {
            $('#adminServicesList').html('<tr><td colspan="8" class="muted">Не удалось загрузить.</td></tr>');
        }
    }

    function openServiceModal(service) {
        const $form = $('#serviceForm');
        $form.trigger('reset');
        $form.find('.js-service-error').text('').addClass('hidden');

        if (service) {
            $('#serviceModalTitle').text('Редактировать услугу');
            $form.find('[name="id"]').val(service.id);
            $('#serviceCategory').val(service.category);
            $('#serviceIcon').val(service.icon || '⚙');
            $('#serviceTitle').val(service.title);
            $('#serviceDescription').val(service.description);
            $('#servicePrice').val(service.price_from);
            $('#serviceUnit').val(service.price_unit || '');
            $('#serviceOrder').val(service.order || 0);
            $('#serviceActive').prop('checked', service.is_active);
        } else {
            $('#serviceModalTitle').text('Новая услуга');
            $form.find('[name="id"]').val('');
            $('#serviceIcon').val('⚙');
            $('#serviceActive').prop('checked', true);
        }

        $('#serviceModal').removeClass('hidden');
        $('body').addClass('modal-open');
    }

    function closeServiceModal() {
        $('#serviceModal').addClass('hidden');
        $('body').removeClass('modal-open');
    }

    $(document).on('click', '.js-service-add', function() { openServiceModal(null); });
    $(document).on('click', '.js-service-edit', function() {
        const id = $(this).data('id');
        API.get('/admin/services/?page_size=1000').then(function(data) {
            const services = (data && data.results) || data || [];
            const svc = services.find(s => String(s.id) === String(id));
            openServiceModal(svc);
        }).catch(function() {
            showToast('Не удалось загрузить услугу.', 'error');
        });
    });
    $(document).on('click', '.js-service-modal-close', closeServiceModal);

    $('#serviceForm').on('submit', async function(e) {
        e.preventDefault();
        const $form = $(this);
        const id = $form.find('[name="id"]').val();
        const $btn = $form.find('button[type=submit]');
        const $err = $form.find('.js-service-error');
        $err.text('').addClass('hidden');

        const data = {
            category: $('#serviceCategory').val(),
            icon: $('#serviceIcon').val() || '⚙',
            title: $('#serviceTitle').val(),
            description: $('#serviceDescription').val(),
            price_from: parseInt($('#servicePrice').val(), 10),
            price_unit: $('#serviceUnit').val() || 'за м²',
            order: parseInt($('#serviceOrder').val() || 0, 10),
            is_active: $('#serviceActive').is(':checked'),
        };

        $btn.prop('disabled', true).text('Сохранение...');
        try {
            if (id) {
                await API.patch('/admin/services/' + id + '/', data);
                showToast('Услуга обновлена');
            } else {
                await API.post('/admin/services/', data);
                showToast('Услуга добавлена');
            }
            closeServiceModal();
            refreshServices();
        } catch (err) {
            let msg = err.message || 'Не удалось сохранить услугу';
            if (err.data) {
                for (const key in err.data) {
                    const v = err.data[key];
                    if (Array.isArray(v)) { msg = v[0]; break; }
                    if (typeof v === 'string') { msg = v; break; }
                }
            }
            $err.text(msg).removeClass('hidden');
        } finally {
            $btn.prop('disabled', false).text('Сохранить услугу');
        }
    });

    $(document).on('click', '.js-service-delete', function() {
        const $btn = $(this);
        const id = $btn.data('id');
        askConfirm(
            'Удалить услугу?',
            '<p class="muted">Связанные работы и заявки могут потерять привязку.</p>',
            'Удалить',
            async function() {
                $btn.prop('disabled', true);
                try {
                    await API.delete('/admin/services/' + id + '/');
                    showToast('Услуга удалена');
                    refreshServices();
                } catch (err) {
                    showToast(err.message || 'Не удалось удалить услугу', 'error');
                    $btn.prop('disabled', false);
                }
            }
        );
    });

    /* ============ О нас ============ */
    var aboutState = { id: null, images: [], removed: [], newFiles: [] };

    function renderAboutImages() {
        const items = [];
        aboutState.images.forEach(function(im) {
            if (aboutState.removed.indexOf(im.id) !== -1) return;
            items.push('<div class="work-img-item">' +
                '<img src="' + esc(im.image) + '" alt="">' +
                '<button type="button" class="work-img-remove" data-kind="about" data-old-id="' + im.id + '" aria-label="Удалить фото">&times;</button></div>');
        });
        aboutState.newFiles.forEach(function(f, idx) {
            items.push('<div class="work-img-item work-img-new">' +
                '<img src="' + URL.createObjectURL(f) + '" alt="">' +
                '<button type="button" class="work-img-remove" data-kind="about" data-new-idx="' + idx + '" aria-label="Удалить фото">&times;</button></div>');
        });
        $('#aboutImgList').html(items.join(''));
    }

    async function refreshAbout() {
        try {
            const data = await API.get('/admin/about/');
            aboutState = { id: data.id, images: data.images || [], removed: [], newFiles: [] };
            $('#aboutDescription').val(data.description || '');
            $('#aboutPublished').prop('checked', !!data.is_published);
            renderAboutImages();
        } catch (e) {
            showToast('Не удалось загрузить «О нас».', 'error');
        }
    }

    $('#aboutImgInput').on('change', function() {
        const files = Array.prototype.slice.call(this.files || []);
        if (files.length) {
            aboutState.newFiles.push.apply(aboutState.newFiles, files);
        }
        this.value = '';
        renderAboutImages();
    });

    $(document).on('click', '.work-img-remove', function() {
        const kind = $(this).data('kind');
        const oldId = $(this).data('old-id');
        if (kind === 'about') {
            if (oldId !== undefined) {
                aboutState.removed.push(oldId);
            } else {
                aboutState.newFiles.splice($(this).data('new-idx'), 1);
            }
            renderAboutImages();
        }
    });

    $(document).on('click', '.js-about-save', async function() {
        const $btn = $(this);
        const $err = $('.js-about-error');
        $err.text('').addClass('hidden');

        const data = new FormData();
        data.append('description', $('#aboutDescription').val() || '');
        data.append('is_published', $('#aboutPublished').is(':checked') ? 'true' : 'false');
        aboutState.newFiles.forEach(function(f) {
            data.append('images', f, f.name);
        });
        if (aboutState.removed.length) {
            data.append('remove_images', JSON.stringify(aboutState.removed));
        }

        $btn.prop('disabled', true).text('Сохранение...');
        try {
            await API.put('/admin/about/', data, true);
            showToast('«О нас» сохранено');
            aboutState.newFiles = [];
            aboutState.removed = [];
            refreshAbout();
        } catch (err) {
            let msg = err.message || 'Не удалось сохранить';
            if (err.data) {
                for (const key in err.data) {
                    const v = err.data[key];
                    if (Array.isArray(v)) { msg = v[0]; break; }
                    if (typeof v === 'string') { msg = v; break; }
                }
            }
            $err.text(msg).removeClass('hidden');
        } finally {
            $btn.prop('disabled', false).text('Сохранить «О нас»');
        }
    });

    /* ===== Закрытие модалок по оверлею и Escape ===== */
    $(document).on('mousedown', '#workModal, #serviceModal, #confirmModal', function(e) {
        if (e.target === this) {
            closeWorkModal();
            closeServiceModal();
            closeConfirm();
        }
    });
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') {
            closeWorkModal();
            closeServiceModal();
            closeConfirm();
        }
    });
});