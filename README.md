# Stories profiler

Скрипт создан для исследования писателей-понифагов с использованием метода TF-IDF и текстового корпуса в 23 миллиона слов (207 крупнейших рассказов с ponyfiction.org)  

TF-IDF вычисляется для каждого слова по очень простой формуле TF x IDF, где:  
TF (Term Frequency) — частота слова в тексте, я взял просто количество повторений.  
IDF (Inverse Document Frequency) — величина, обратная количеству текстов, содержащих в себе это слово.  
Я взял log(N/n), где N — общее кол-во текстов в выборке, n — кол-во текстов, в которых есть это слово.  

Инструмент получился довольно шустрым и универсальным. Найти ключевые слова в чат-логе, вычислить автора созданной под псевдонимом книги, распределить тексты по лексике — игрушка может всё это и даже больше. Всё что нужно, это размер текстов хотя бы в 30 000 слов и пара-тройка сотен случайных книг.

## Установка

Скрипты проверялись только на GNU/Linux.  
`git clone https://github.com/Shadybloom/stories-profiler`  
Нужен питон третьей версии, например Python 3.7, а также sqlite3.  
`sudo apt-get update && sudo apt-get install python3.7 sqlite3`  
Кроме того понадобятся внешние библиотеки Python (можно установить в каталог пользователя):  
`pip install --user pymorphy2`  

## Генерация базы данных

Перейдём в каталог скрипта:  
`cd ./stories-profiler`  
Создадим рабочий каталог:  
`mkdir -p ./data/ponyfiction_fb2`  
Запускаем генерацию базы данных:  
`./gen_database.py data/ponyfiction_fb2`  

Процесс можно прервать в любое мгновение, данные сохраняются. Сначала обрабатываются книги (если в конфиге указано `MORPHY_SOFT = True` то довольно медленно), затем создаются таблицы токенов, после этого вычисляется TF-IDF и граф связей.  

Если нужно обновить базу данных, достаточно дать скрипту любую новую книгу, или поставить в конфиге:  
`regen_words_table = True`  

## Поиск в базе данных

Есть втроенный поисковик:  
`./database_search.py Янтарь`  
Вывод характерных для рассказа слов/фраз:  
`./database_search.py -o Янтарь`  
Вывод используемых скриптом поисковых токенов:  
`./database_search.py -p Янтарь`  
Вывод того же, но в файл и без ограничения строк:  
`./database_search.py -L 10000 Янтарь > /tmp/tokens.txt`  

## Скриншоты

![Пример](/images/example3.png)  
![Пример](/images/example4.png)  
![Попался](/images/catched.png)  

## Заметки:

В строении базы данных есть фундаментальная ошибка. Чем больше книг в бд, тем больше оперативной памяти требует построение таблицы: скрипт жрёт и жрёт RAM, вот прямо как свинья. В выборках до тысячи книг (миллионы токенов) это не заметно, но в серьёзной работе понадобится гораздо большая база данных и чувствительность.  

**Решение:**  
Записываем и слова, и фразы в единственную таблицу. Не перебирая. Когда книги будут загружены, начинаем идти снизу таблицы, захватывая и помечая группами одинаковые токены. Да, речь идёт о миллионах, десятках миллионов поисковых запросов, это будет неспешный процесс, зато очень надёжный и непрерывный.  

**Думаем над новым форматом базы данных:**  
* raw - таблица из частотных словарей слов и фраз:  
`phrase_id, source_id, frequency, word/phrase, used_mark`  
sources - таблица с общими данными по книге:  
`source_id, wordcount, phrasecount, файл, название, автор`  
corpora - таблица обработанных слов и фраз:  
`token_id, source_id, sum_frequency, storycount, word/phrase, файл, название, автор`  

**Детали:**
Вопрос, как нам перебрать токены, чтобы передать уникальные в таблицу phrases?  
Берём группой, обрабатываем, передаём, на остальные ставим метку. Единичку.  
>SQLite does not have a separate Boolean storage class. Instead, Boolean values are stored as integers 0 (false) and 1 (true).  

Так можно увеличить значение:  
`UPDATE {Table} SET {Column} = {Column} + {Value} WHERE {Condition}`  

Сначала заносим данные в raw и sources, затем потихоньку обрабатываем.  
