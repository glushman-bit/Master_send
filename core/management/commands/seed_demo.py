import hashlib
import math
import random
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from portfolio.models import PortfolioItem, PortfolioImage
from prices.models import PriceTable
from services.models import Service

W, H = 800, 500


def hex_rgb(value: str):
    """Преобразует hex-строку цвета в кортеж (R, G, B)."""
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mix(c1, c2, t):
    """Интерполирует два цвета с коэффициентом t от 0 до 1."""
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def _shade(color, factor):
    """Затемняет или осветляет цвет, умножая каналы на factor."""
    return tuple(max(0, min(255, round(c * factor))) for c in color)


# Объект целиком для одного «фото» — чтобы работало как с PNG-оверлеем, так и без.
def make_image(label: str, bg_top, bg_bottom, slug: str, disc_color, dirty: bool = False) -> ContentFile:
    """Генерирует фотореалистичную картинку работы: мастерская + диск в 3D-градиенте."""
    rng = random.Random(slug)
    bg_top = hex_rgb(bg_top)
    bg_bottom = hex_rgb(bg_bottom)
    disc = hex_rgb(disc_color)

    img = Image.new('RGB', (W, H))
    px = img.load()

    # --- Задник: вертикальный градиент + слабая «стена/пол» ---
    floor_y = 350
    for y in range(H):
        if y < floor_y:
            t = y / floor_y
            row = _mix(bg_top, bg_bottom, t)
        else:
            t = (y - floor_y) / (H - floor_y)
            row = _shade(_mix(bg_bottom, (26, 26, 28), t), 0.82)
        for x in range(W):
            px[x, y] = row

    # Лёгкий шум для фактуры
    for _ in range(12000):
        x = rng.randrange(W)
        y = rng.randrange(H)
        o = rng.randint(-9, 9)
        px[x, y] = tuple(max(0, min(255, c + o)) for c in px[x, y])

    cx, cy, radius = 400, 250, 138

    draw = ImageDraw.Draw(img)

    # --- Тень на полу под диском ---
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for k in range(8, 0, -1):
        r = int(radius * (0.75 + 0.05 * (8 - k)))
        sd.ellipse([cx - r, cy + 26 - int(r * 0.62), cx + r, cy + 26 + int(r * 0.62)],
                   fill=(0, 0, 0, 26))
    img = Image.alpha_composite(img.convert('RGBA'), shadow)
    draw = ImageDraw.Draw(img)

    # --- Диск: радиальная металлическая поверхность ---
    # Внутренний массив пикселей диска с источником света сверху-слева
    for yy in range(cy - radius, cy + radius):
        for xx in range(cx - radius, cx + radius):
            dx = (xx - cx) / radius
            dy = (yy - cy) / radius
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            # ламбертово освещение сфероида
            nx, ny = dx, dy
            nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
            light = max(0.0, 0.55 * nx + 0.8 * ny + 0.65 * nz)
            light = max(0.15, min(1.0, light))
            # лёгкие металлические «кольца» (обработка после пескоструя)
            ring = 0.25 * (1 + math.sin(d2 * 46))
            base = tuple(round(c * (0.55 + 0.5 * light)) for c in disc)
            col = tuple(max(0, min(255, round(b + ring * 22))) for b in base)
            px[xx, yy] = col

    # --- Обод: тёмное кольцо (резина/край диска) ---
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 outline=(8, 8, 10), width=14)

    # --- Спицы: затемнение клиньями ---
    spoke_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd2 = ImageDraw.Draw(spoke_img)
    for i in range(6):
        a0 = math.radians(i * 60 - 15)
        a1 = math.radians(i * 60 + 15)
        pts = [(cx, cy)]
        for a in (a0, a1):
            pts.append((cx + math.cos(a) * radius * 0.97, cy + math.sin(a) * radius * 0.97))
        sd2.polygon(pts, fill=(25, 25, 30, 130))
    img = Image.alpha_composite(img, spoke_img)
    draw = ImageDraw.Draw(img)

    # --- Болты по кругу ---
    for i in range(5):
        a = math.radians(i * 72 + 18)
        bx = round(cx + math.cos(a) * radius * 0.68)
        by = round(cy + math.sin(a) * radius * 0.68)
        draw.ellipse([bx - 8, by - 8, bx + 8, by + 8], fill=_shade(disc, 0.85), outline=(28, 28, 32), width=2)
        draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=_shade(disc, 1.25))

    # --- Ступица центр ---
    draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=_shade(disc, 0.7), outline=(28, 28, 32), width=3)
    draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=_shade(disc, 1.3), outline=(40, 40, 46), width=2)

    # --- Блик ---
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.ellipse([cx - radius + 22, cy - radius + 16, cx + radius - 70, cy + radius - 100], fill=(255, 255, 255, 34))
    img = Image.alpha_composite(img, gl)
    draw = ImageDraw.Draw(img)

    if dirty:
        # --- Грязь/ржавчина на «до» ---
        dirt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dirt)
        for i in range(70):
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0, radius - 6)
            bx = cx + math.cos(a) * rr
            by = cy + math.sin(a) * rr
            s = rng.randint(4, 20)
            dcol = rng.choice([(92, 74, 46, 140), (72, 64, 52, 150), (110, 96, 60, 120), (60, 52, 42, 160)])
            dd.ellipse([bx - s, by - s, bx + s, by + s], fill=dcol)
        img = Image.alpha_composite(img, dirt)
        draw = ImageDraw.Draw(img)

    # --- Скруглённая рамка ---
    frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle([6, 6, W - 7, H - 7], radius=10, outline=(255, 255, 255, 46), width=4)
    img = Image.alpha_composite(img, frame)
    draw = ImageDraw.Draw(img)

    # --- Виньетка ---
    vig = Image.new('L', (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, W, H], fill=70)
    for k in range(30, 0, -1):
        m = int(k * 2.1)
        vd.rounded_rectangle([m, m, W - m, H - m], radius=10, fill=0)
    img = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), img.convert('RGB'), vig)

    # --- Подпись ---
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([W - 190, 26, W - 26, 80], radius=12, fill=(0, 0, 0, 170))
    draw.text((W - 108, 53), label, fill='#ffffff', anchor='mm', font_size=30)

    buf = BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=88)
    return ContentFile(buf.getvalue(), name=f'work_{slug}.jpg')


def image_slug(title: str) -> str:
    """Возвращает стабильный короткий идентификатор изображения по названию."""
    return hashlib.md5(title.encode('utf-8')).hexdigest()[:10]


class Command(BaseCommand):
    help = 'Заполняет базу тестовыми услугами и работами для портфолио.'

    SERVICES = [
        {
            'category': Service.Category.SAND,
            'title': 'Пескоструйная обработка металла',
            'description': 'Очистка поверхностей от ржавчины, окалины и старой краски перед покраской.',
            'price_from': 1500,
            'price_unit': 'за м²',
            'icon': '🪨',
        },
        {
            'category': Service.Category.SAND,
            'title': 'Пескоструй дисков',
            'description': 'Подготовка литых и кованых дисков к покраске: удаляем коррозию и старые покрытия.',
            'price_from': 800,
            'price_unit': 'за диск',
            'icon': '⚙',
        },
        {
            'category': Service.Category.POWDER,
            'title': 'Порошковая покраска металла',
            'description': 'Стойкое полимерное покрытие для любых металлических изделий: до 15 лет службы.',
            'price_from': 2000,
            'price_unit': 'за м²',
            'icon': '🎨',
        },
        {
            'category': Service.Category.POWDER,
            'title': 'Порошковая покраска дисков',
            'description': 'Красим диски в любой цвет по RAL. Пескоструй и покраска под ключ.',
            'price_from': 1200,
            'price_unit': 'за диск',
            'icon': '🛞',
        },
        {
            'category': Service.Category.WELD,
            'title': 'Сварочные работы',
            'description': 'Аргонная и полуавтоматическая сварка: заборы, ворота, рамы, каркасы.',
            'price_from': 500,
            'price_unit': 'за погонный метр',
            'icon': '👨‍🏭',
        },
        {
            'category': Service.Category.WELD,
            'title': 'Изготовление металлоконструкций',
            'description': 'Чертежи, изготовление и монтаж металлоконструкций любой сложности.',
            'price_from': 10000,
            'price_unit': 'за проект',
            'icon': '🔧',
        },
    ]

    PORTFOLIO = [
        # (title, category, tags, bg_top, bg_bottom, disc_color_after)
        ('Пескоструй и покраска дисков BMW', Service.Category.SAND, 'пескоструй, порошковая покраска', '#b8bec6', '#5b636e', '#c8a23a'),
        ('Кованые диски Audi — восстановление', Service.Category.SAND, 'пескоструй, порошок RAL 1015', '#c2bfb2', '#6a665a', '#d9d2ba'),
        ('Забор из профнастила', Service.Category.WELD, 'сварка, порошковая покраска', '#8a927b', '#3a4032', '#7a8a5a'),
        ('Распашные ворота с калиткой', Service.Category.WELD, 'сварка, грунт, покраска', '#b0a48c', '#5a4e3a', '#8a5a3a'),
        ('Бампер внедорожника — чёрный мат', Service.Category.POWDER, 'порошковая покраска RAL 9005', '#8b929b', '#3d4248', '#292c30'),
    ]

    PRICE_TABLES = [
        {
            'title': 'Стоимость покраски дисков, руб',
            'description': 'Предлагаем покраску дисков порошковой краской, цена на которую включает: '
                           'пескоструйную обработку, порошковую грунтовку и порошковую покраску всей поверхности диска.',
            'order': 1,
            'cells': [
                [
                    'диаметр диска',
                    'легкосплавные литые и кованные диски без гальв. покрытия',
                    'легкосплавные литые и кованные диски с гальв. покрытием',
                    'стальные диски',
                ],
                ['До D 10', '5000,00', '6000,00', '2000,00'],
                ['D 10 – D 12', '6000,00', '7000,00', '2500,00'],
                ['D 13 – D 15', '7000,00', '8000,00', '3000,00'],
                ['D 16 – D 18', '8000,00', '9000,00', '3500,00'],
                ['D 19 – D 21', '9500,00', '10500,00', '4000,00'],
                ['D 22 и более', '11000,00', '12000,00', '4500,00'],
            ],
        },
        {
            'title': 'Дополнительные услуги',
            'description': 'Работы, которые могут потребоваться при покраске дисков.',
            'order': 2,
            'cells': [
                ['Наименование', 'Ед. измерения', 'Стоимость, руб'],
                ['Пескоструйная обработка диска', 'шт', '1000,00'],
                ['Демонтаж и монтаж шин (без снятия)', 'шт', '500,00'],
                ['Снятие и установка диска с автомобиля', 'шт', '300,00'],
                ['Услуга разбортировки / забортировки', 'шт', '200,00'],
                ['Упаковка дисков', 'шт', '100,00'],
            ],
        },
    ]

    def add_arguments(self, parser):
        """Добавляет аргумент командной строки --flush."""
        parser.add_argument(
            '--flush', action='store_true',
            help='Удалить существующие услуги и работы перед заполнением.',
        )

    def _reset_images(self, item):
        """Удаляет все фото работы с диска и из БД."""
        for img in item.images.all():
            if img.image and img.image.name:
                img.image.storage.delete(img.image.name)
            img.delete()

    def _add_image(self, item, kind, label, bg_top, bg_bottom, disc_color, dirty, slug):
        """Создаёт одно синтетическое фото работы."""
        order = item.images.filter(kind=kind).count()
        PortfolioImage.objects.create(
            item=item,
            kind=kind,
            image=make_image(label, bg_top, bg_bottom, slug, disc_color, dirty=dirty),
            order=order,
        )

    def handle(self, *args, **options):
        """Заполняет базу тестовыми услугами и работами портфолио."""
        if options['flush']:
            for item in PortfolioItem.objects.all():
                self._reset_images(item)
            PortfolioItem.objects.all().delete()
            Service.objects.all().delete()
            PriceTable.objects.all().delete()
            self.stdout.write(self.style.WARNING('Существующие данные удалены.'))

        for s in self.SERVICES:
            Service.objects.update_or_create(
                title=s['title'],
                defaults={
                    'category': s['category'],
                    'description': s['description'],
                    'price_from': s['price_from'],
                    'price_unit': s['price_unit'],
                    'icon': s['icon'],
                    'is_active': True,
                },
            )

        services_by_category = {
            category: Service.objects.filter(category=category).first()
            for category in (Service.Category.SAND, Service.Category.POWDER, Service.Category.WELD)
        }

        for title, category, tags, bg_top, bg_bottom, disc_color in self.PORTFOLIO:
            obj, _ = PortfolioItem.objects.get_or_create(
                title=title, defaults={'service': services_by_category[category]}
            )
            obj.service = services_by_category[category]
            obj.description = f'Пример работы: {tags}.'
            obj.is_published = True
            obj.save()
            self._reset_images(obj)
            before_slug = image_slug(obj.title) + '_before'
            self._add_image(obj, PortfolioImage.Kind.BEFORE, 'ДО', '#9aa0a8', '#4c525a', '#6a6d72', dirty=True, slug=before_slug)
            after_slug = image_slug(obj.title)
            self._add_image(obj, PortfolioImage.Kind.AFTER, 'ПОСЛЕ', bg_top, bg_bottom, disc_color, dirty=False, slug=after_slug)
            variant = '#%02x%02x%02x' % _shade(hex_rgb(disc_color), 1.18)
            self._add_image(obj, PortfolioImage.Kind.AFTER, 'ПОСЛЕ 2', bg_top, bg_bottom, variant, dirty=False, slug=after_slug + '_v2')

        for table in self.PRICE_TABLES:
            PriceTable.objects.update_or_create(
                title=table['title'],
                defaults={
                    'description': table['description'],
                    'cells': table['cells'],
                    'order': table['order'],
                    'is_published': True,
                },
            )

        services_count = Service.objects.count()
        portfolio_count = PortfolioItem.objects.count()
        prices_count = PriceTable.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Готово: услуг {services_count}, работ в портфолио {portfolio_count}, таблиц цен {prices_count}.'
        ))