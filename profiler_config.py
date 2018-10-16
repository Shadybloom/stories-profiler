BOOKS_DIR = '.data/ponyfiction_fb2'
DATABASE_DIR = 'database'
TOKENS_DICT = 'database/tokens.pickle'
DATABASE_PATH = 'database/stories.sqlite'
# Нормализация слов с помощью pymorphy:
MORPHY_SOFT = True
MORPHY_FORCED = False
# Хранить текст не обязательно, достаточно списков:
SAVE_BOOK_TEXT = False
# Разбиваем фразы на токены (группы из 2-3 слов)
PHRASES_TOKENIZE = True
# Минимальное число совпадений фразы для выборки в словарь:
PHRASEFREQ_MIN = 2
# Минимальные и максимальные значения tf-idf для построения облака ссылок:
SCORE_MIN = 5
SCORE_MAX = 5000
# С каждым новым текстом в бд таблица всё равно пересоздаётся:
regen_words_table = False
# Строк в выводе:
OUTPUT_LINES = 20
