// Манифест 8 модулей «Нейро-шеф Гурмикс» — зеркало публичных полей
// backend/app/modules/registry.py. Бэкенд — источник истины; этот файл нужен,
// чтобы экран выбора модулей рендерился без round-trip. В рантайме можно
// дополнительно подтянуть GET /api/v1/modules и слить (актуальный status и т.д.).
//
// accent — CSS-переменная из tokens.css (--ark-av-1 ... --ark-av-8).

export type ModuleStatus = 'active' | 'locked'
export type ModuleMode = 'rag' | 'llm' | 'tool' | 'db' | 'static'

export interface BotModule {
  id: string
  title: string
  short: string
  emoji: string
  accent: string
  order: number
  status: ModuleStatus
  mode: ModuleMode
  examples: string[]
}

export const MODULES: BotModule[] = [
  {
    id: 'product-expert',
    title: 'Продуктовый эксперт Гурмикс',
    short: 'Ассортимент: категории, наличие, подбор по каталогу',
    emoji: '📦',
    accent: '--ark-av-3',
    order: 1,
    status: 'active',
    mode: 'rag',
    examples: [
      'Какие соусы азиатские есть?',
      'Что входит в категорию маринады?',
      'Есть ли у вас рассолы для копчения?',
    ],
  },
  {
    id: 'technologist',
    title: 'Технолог пищевого производства',
    short: 'Нормы закладки, потери, выход, пищевая безопасность, маркировка',
    emoji: '🔬',
    accent: '--ark-av-5',
    order: 2,
    status: 'locked',
    mode: 'rag',
    examples: ['Какие потери при заморозке у продукта X?', 'Норма закладки на порцию 250 г?'],
  },
  {
    id: 'brand-chef',
    title: 'Бренд-шеф · взгляд Артура',
    short: 'Адаптация под ресторан, фабрику-кухню, ритейл, доставку',
    emoji: '👨‍🍳',
    accent: '--ark-av-1',
    order: 3,
    status: 'locked',
    mode: 'rag',
    examples: ['Как адаптировать блюдо под доставку?', 'Идея для витрины на основе продуктов Гурмикс?'],
  },
  {
    id: 'ttk-generator',
    title: 'Генератор ТТК и расчётов',
    short: 'Базовая ТТК / рецептурный расчёт, пересчёт на порцию · 1 · 50 · 100 кг',
    emoji: '📊',
    accent: '--ark-av-6',
    order: 4,
    status: 'locked',
    mode: 'tool',
    examples: ['Сделай ТТК на 50 кг для блюда на основе соуса Гурмикс', 'Пересчитай рецептуру на 1 порцию'],
  },
  {
    id: 'commercial',
    title: 'Коммерческий консультант',
    short: 'Расход и стоимость продукта на порцию · 1 кг · партию · блюдо',
    emoji: '💰',
    accent: '--ark-av-4',
    order: 5,
    status: 'locked',
    mode: 'rag',
    examples: ['Сколько стоит продукт на порцию 200 г?', 'Себестоимость соуса на партию 30 кг?'],
  },
  {
    id: 'retail-factory',
    title: 'Эксперт по ритейлу и фабрикам-кухням',
    short: 'Крупные объёмы, витрина, вакуумные маринады, полуфабрикаты, сети',
    emoji: '🏭',
    accent: '--ark-av-2',
    order: 6,
    status: 'active',
    mode: 'llm',
    examples: ['Как организовать вакуумные маринады на фабрике-кухне?', 'Решение для витрины полуфабрикатов в сети?'],
  },
  {
    id: 'trend-analyst',
    title: 'Тренд-аналитик',
    short: 'Тренды HoReCa, ритейла, доставки, азиатской кухни, сезонных меню',
    emoji: '📈',
    accent: '--ark-av-7',
    order: 7,
    status: 'active',
    mode: 'llm',
    examples: ['Какие тренды в доставке азиатской кухни сейчас?', 'Идея сезонного меню на осень с продуктами Гурмикс?'],
  },
  {
    id: 'distributors',
    title: 'Справочник по дистрибьюторам',
    short: 'Как и где закупить продукцию · каналы поставок · заявка на контакты',
    emoji: '📍',
    accent: '--ark-av-8',
    order: 8,
    status: 'active',
    mode: 'llm',
    examples: ['Где купить в Новосибирске?', 'Есть дистрибьютор в Краснодарском крае?'],
  },
]

export const MODULES_BY_ID: Record<string, BotModule> = Object.fromEntries(
  MODULES.map((m) => [m.id, m]),
)
