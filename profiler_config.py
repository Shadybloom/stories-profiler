#BOOKS_DIR = 'data/ponyfiction_fb2'
DATABASE_DIR = 'database'
TOKENS_DICT = 'database/tokens.pickle'
DATABASE_PATH = 'database/stories.sqlite'
OPENCORPORA_DICT = '/dicts/opencorpora-sing-nom.sqlite'
# Нормализация слов с помощью pymorphy (soft -- не трогает неологизмы):
MORPHY_SOFT = True
MORPHY_FORCED = False
# Хранить текст не обязательно, достаточно списков:
SAVE_BOOK_TEXT = False
# Разбиваем фразы на токены (группы из 2-3 слов)
PHRASES_TOKENIZE = True
# Чтобы отбрасывать дубликаты нужна готовая БД:
REJECT_DUPLICATES = False
# Больше 10 -- почти наверняка дубль
REJECT_SCORE = 15
# Минимальное число совпадений фразы для выборки в словарь:
PHRASEFREQ_MIN = 2
# Минимальные и максимальные значения tf-idf для построения облака ссылок:
SCORE_MIN = 1
SCORE_MAX = 5000
# Строк в выводе:
OUTPUT_LINES = 20

# Опции вывода graphviz:
# Вывод в файл:
IMG_DIR = 'output'
# Число проходов цикла:
RECURSION_LVL = 5
# Чувствительность:
SIMILARITY_SCORE_MIN = 0.0
SIMILARITY_MAX = 200
# Число нод в выводе:
NODES_MAX = 20
