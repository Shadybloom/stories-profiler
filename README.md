# Stories profiler

Скрипт создан для исследования писателей-понифагов с использованием метода TF-IDF и текстового корпуса в 69 миллионов слов (1300 крупнейших рассказов с ponyfiction.org и ficbook). Ниже пример атаки пересечения: обнаружение схожих текстов по характерным для них словам и фразам.  

![Крутота](/images/wow.png)  
![Поиск подобных](/images/compare2.png)  
![Поиск подобных](/images/compare.png)  
![Обнаружение](/images/detect.png)  
![Исследование автора](/images/analysis.png)  

## Как это работает

* Мы создаём частотные словари для слов и фраз в два-три слова, так определяя самые частые слова/фразы в рассказе.
* На основе частотных словарей строится текстовый корпус: слово -- число рассказов с этим словом -- топовый рассказ (по частоте слова в процентах)
* Затем для каждого текста в базе данных создаются словари TF-IDF. То есть рейтинг слов, где на вершину попадают не бесполезные союзы, а имена персонажей и уникальные названия.
* Из словарей TF-IDF строятся облака ссылок. Частое слово -- топовый рассказ с этим словом -- рейтинг связей других рассказов с точки зрения обрабатываемого текста.
* На этом база данных готова. Можно играть с поисковиком и собирать любопытные данные, но самое крутое скрыто в перекрёстных ссылках между рассказами.
* Чтобы получить граф связей мы берём какой-нибудь рассказ и рекурсивно обходим прочие по идущим от него ссылкам. Но в вывод попадают только те рассказы, в которых есть ответная ссылка на вершину. Так мы определяем автора группы текстов.
* Быстро, качественно, простейшими логарифмами. И да, на технологиях восьмидесятых, без каких-либо нейросетей.

### Пояснение к терминам

TF-IDF вычисляется для каждого слова по очень простой формуле TF x IDF, где:  
TF (Term Frequency) — частота слова в тексте, я взял просто количество повторений.  
IDF (Inverse Document Frequency) — величина, обратная количеству текстов, содержащих в себе это слово.  
Я взял log(N/n), где N — общее кол-во текстов в выборке, n — кол-во текстов, в которых есть это слово.  

### Постскриптум

Инструмент получился довольно шустрым и универсальным. Найти ключевые слова в чат-логе, вычислить автора созданной под псевдонимом книги (или постов на форуме), распределить тексты по лексике — игрушка может всё это и даже больше. Результаты говорят сами за себя.

И, наконец, эта штука ещё и работает быстро! Текстовый корпус в 70 миллионов слов обрабатывается всего за несколько минут, а запросы и вовсе занимают жалкие доли секунды, ведь всё нужное уже хранится внутри БД.

## Установка

Скрипты проверялись только на GNU/Linux (но так-то должны работать везде).  
`git clone https://github.com/Shadybloom/stories-profiler`  
Нужен питон третьей версии, например Python 3.7, а также sqlite3.  
`sudo apt-get update && sudo apt-get install python3.7 sqlite3`  
Кроме того понадобятся внешние библиотеки Python (можно установить в каталог пользователя):  
`pip install --user pymorphy2 graphviz`  

Pymorphy используется для нормализации слов. Особой необходимости в этом нет, если поставить в конфиге `MORPHY_SOFT = False` то скрипт будет запускаться и без него.

Graphviz, очевидно, отвечает за вывод графов. Если не использовать графический вывод в database_graph.py, то без него тоже можно обойтись.  

## Генерация базы данных

Перейдём в каталог скрипта:  
`cd ./stories-profiler`  
Создадим каталоги для базы данных и текстов:  
`mkdir ./database ; mkdir -p ./data/ponyfiction_fb2`  
Создаём список ссылок на понифики как минимум в 10k слов:  
`words=10000 ; curl -A "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" "https://ponyfiction.org/search/?q=&type=0&sort=0&original=1&min_words=$words&page=[1-100]" | egrep 'download' | sed 's/.*href="/https:\/\/ponyfiction.org/' | sed 's/" class=.*//' > data/urls.txt`  
Загружаем файлы по списку ссылок в рабочий каталог (в 10 потоков, чтобы быстрее):  
`cat ./data/urls.txt | xargs -t -P 10 -n1 wget "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" -P data/ponyfiction_fb2`  
Запускаем генерацию базы данных:  
`./gen_database.py data/ponyfiction_fb2`  

Процесс можно прервать в любое мгновение, данные сохраняются. Сначала обрабатываются книги (если в конфиге указано `MORPHY_SOFT = True` то довольно медленно), затем создаются таблицы токенов, после этого вычисляется TF-IDF и граф связей.  

Выбор другой базы данных:  
`./gen_database.py -D database/ficbook.sqlite`  
Пополнение базы данных с отбрасыванием дубликатов (не работает без tokens.pickle):  
`./gen_database.py -r /data/ficbook_fb2/`  
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

## Графический вывод

Есть встроенный поисковик:  
`./database_graph.py Янтарь`  
`./database_graph.py В облаках пушист`  
Вывод картинки сразу на экран (нужен sxiv):  
`./database_graph.py Стальные крылья -o | sxiv -f -`  
Выбор чувствительности поисковика (не больше числа текстов в БД):  
`./database_graph.py Стальные крылья -o -s 400 | sxiv -f -`  
Выбор числа узлов на выходе (больше — медленнее):  
`./database_graph.py Стальные крылья -o -s 400 -n 50 | sxiv -f -`  

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

## База данных флибусты

**Список из 1000 самых популярных книг:**  
`curl -A "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" "http://flibustahezeous3.onion/stat/b?page=[0-9]" |  egrep -o '\- <a href="/b/[0-9]+">' | sed 's|- <a href="|http://flibustahezeous3.onion|' | sed 's|">|/fb2|' > /tmp/urls.txt`

**Загружаем книги по списку:**  
```
mkdir /tmp/flibusta_top_fb2 ; cd /tmp/flibusta_top_fb2
while read url;
do
name=`echo $url | egrep -o '[0-9][0-9]+' | sed 's/\(.*\)/\1.fb2/'`
echo "$name"
wget -q -U 'Mozilla/5.0 (Windows NT 6.1; rv:38.0) Gecko/20100101 Firefox/38.0' $url -O $name                              
done < /tmp/urls.txt
```

40 книг из списка не перевариваются декодером. Кот знает, что с ними не так.  

## База данных самиздата

**Список из 2000 книг, жанр фэнтези:**  
`curl -A "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0" "http://samlib.ru/janr/index_janr_hits24-[1-10].shtml" | egrep -o ': <a href=.*shtml>' | sed 's|: <a href=|http://samlib.ru|' | sed 's|.shtml>|.shtml|' > /tmp/urls.txt`

**Загружаем книги по списку:**  
```
mkdir ./samlib_top_fb2
while read url;
do
name=`echo $url | sed 's|http://samlib.ru/[a-z]/||' | sed 's|/|-|' | sed 's|.shtml|.fb2|'`
echo "$name"
python samlib_downloader.py "$url" > ./samlib_top_fb2/$name
done < /tmp/urls.txt
```

fb2 есть далеко не ко всем книгам, поэтому делаем скриптом.  
Мусора тоже много, из 2000 книжек получается всего 1400 годных.  

## Авторские слова в диалогах

**Из топа флибусты:**  
```
cd ./data/flibusta_top_fb2/ ; unzip \*.zip
cat ./data/flibusta_top_fb2/*.fb2 | egrep '<p>[–—-]+' | sed 's/<p>[-–—]\+/|||/' | sed 's/<\/p>//' | sed 's/\([–—-][^-–—]\+\)[–—-].*/\1/' | egrep -o '[^а-яА-Я][  ]+[–—-]+[  ]+[а-яА-Я,; -"«»]+'
cat ./data/flibusta_top_fb2/*.fb2 | egrep '<p>[–—-]+' | sed 's/<p>[-–—]\+/|||/' | sed 's/<\/p>//' | sed 's/\([–—-][^-–—]\+\)[–—-].*/\1/' | egrep -o '[^а-яА-Я][  ]+[–—-]+[  ]+[а-яА-Я,; -"«»]+' | ./verb_extract.py | head -n 100
```

**Из топа самиздата:**  
```
cat ./data/samlib_top_fb2/* | egrep '^[  ]+[–—-]+' | sed 's/[-–—]\+/|||/' |  sed 's/\([–—-][^-–—]\+\)[–—-].*/\1/' |  egrep -o  '[^а-яА-Я][  ]+[–—-]+[  ]+[а-яА-Я,; "«»]+'
cat ./data/samlib_top_fb2/* | egrep '^[  ]+[–—-]+' | sed 's/[-–—]\+/|||/' |  sed 's/\([–—-][^-–—]\+\)[–—-].*/\1/' |  egrep -o  '[^а-яА-Я][  ]+[–—-]+[  ]+[а-яА-Я,; "«»]+' | ./verb_extract.py | head -n 100
```

**С понификшена:**  
```
cat ./data/ponyfiction_all_fb2/* | sed 's|><|>\n<|g' | egrep '<p>[^-–—]*[–—-]+' | sed 's/<p>[^-–—]*[-–—]\+/|||/' | sed 's/<\/p>//'  | sed 's/\([–—-][^-–—]\+\)[–—-].*/\1/' | egrep -o '[^а-яА-Я][  ]+[–—-]+[  ]+[а-яА-Я,; -"«»]+'

```

![Пример](/images/dialogs-example.png)  
