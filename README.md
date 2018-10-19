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
Создадим каталог для текстов:  
`mkdir -p ./data/ponyfiction_fb2`  
Создаём список ссылок на понифики как минимум в 10k слов:  
`words=10000 ; curl -A "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" "https://ponyfiction.org/search/?q=&type=0&sort=0&original=1&min_words=$words&page=[1-100]" | egrep 'download' | sed 's/.*href="/https:\/\/ponyfiction.org/' | sed 's/" class=.*//' > data/urls.txt`  
Загружаем файлы по списку ссылок в рабочий каталог (в 10 потоков, чтобы быстрее):  
`cat ./data/urls.txt | xargs -t -P 10 -n1 wget "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" -P data/ponyfiction_fb2`  
Запускаем генерацию базы данных:  
`./gen_database.py data/ponyfiction_fb2`  

Процесс можно прервать в любое мгновение, данные сохраняются. Сначала обрабатываются книги (если в конфиге указано `MORPHY_SOFT = True` то довольно медленно), затем создаются таблицы токенов, после этого вычисляется TF-IDF и граф связей.  

Выбор другой базы данных:  
`./gen_database.py -D database/ficbook.sqlite`  
Если нужно обновить базу данных, достаточно дать скрипту любую новую книгу, или ключ -R:  
`./gen_database.py -R`  

## Поиск в базе данных

Есть втроенный поисковик:  
`./database_search.py Янтарь`  
Вывод характерных для рассказа слов/фраз:  
`./database_search.py -o Янтарь`  
Вывод используемых скриптом поисковых токенов:  
`./database_search.py -t Янтарь`  
Вывод того же, но в файл и без ограничения строк:  
`./database_search.py -t -L 10000 Янтарь > /tmp/tokens.txt`  

## Сравнение с внешними файлами

Вывод ключевых слов:  
`./wordfreq-tf-idf.py ~/chat.log -o`  
Поиск схожих работ в базе данных:  
`cat ~/workspace/amber-in-the-dark/chapters/* | ./wordfreq-tf-idf.py`  
Вывод из буфера обмена (нужен xclip):  
`xclip -o | ./wordfreq-tf-idf.py`  

## Скриншоты

![Няшка](/images/cutie.png)  
![Пример](/images/example3.png)  
![Пример](/images/example4.png)  
![Попался](/images/catched2.png)  

## Заметки:

В строении базы данных есть фундаментальная ошибка. Чем больше книг в бд, тем больше оперативной памяти требует построение таблицы: скрипт жрёт и жрёт RAM, вот прямо как свинья. В выборках до тысячи книг (миллионы токенов) это не заметно, но в серьёзной работе понадобится гораздо большая база данных и чувствительность.  

**Решение:**  
Записываем и слова, и фразы в единственную таблицу. Не перебирая. Когда книги будут загружены, начинаем идти снизу таблицы, захватывая и помечая группами одинаковые токены. Да, речь идёт о миллионах, десятках миллионов поисковых запросов, это будет неспешный процесс, зато очень надёжный и непрерывный.  

**Думаем над новым форматом базы данных:**  
* raw - таблица из частотных словарей слов и фраз:  
`phrase_id, source_id, frequency, word/phrase, tf_idf`  
* sources - таблица с общими данными по книге:  
`source_id, wordcount, phrasecount, файл, название, автор, linkscloud`  
* corpora - таблица обработанных слов и фраз:  
`token_id, source_id, sum_frequency, storycount, word/phrase, файл, название, автор`  

**Детали:**  
Вопрос, как нам перебрать токены, чтобы передать уникальные в таблицу phrases?  
Берём группой, обрабатываем, передаём, на остальные ставим метку. Единичку.  
>SQLite does not have a separate Boolean storage class. Instead, Boolean values are stored as integers 0 (false) and 1 (true).  

Вместо used_mark мы пересчитываем для каждого слова tf_idf.  
Хотя, это замедлит работу скрипта. Причём здорово замедлит, но параметр так и так нужно считать.  

Так можно увеличить значение:  
`UPDATE {Table} SET {Column} = {Column} + {Value} WHERE {Condition}`  

Сначала заносим данные в raw и sources, затем потихоньку обрабатываем.  
