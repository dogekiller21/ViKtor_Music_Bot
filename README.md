> **Для запуска бота у себя**
> * **Установите Python3.10 [*(ссылка)*](https://www.python.org/downloads/)**
> * **Скопируйте код бота себе** с помощью `git clone https://github.com/dogekiller21/ViKtor_Music_Bot`
> * **Создайте виртуальное окружение** (в папке проекта `python -m venv venv`)
> * **Активируйте виртуальное окружение** \
(Для Windows: `venv/Scripts/activate.bat` \
Для Linux: `source venv/bin/activate`)
> * **Установите необходимые пакеты** в свое окружение с помощью `pip install -r requirements.txt` \
*(cмотрите ниже о решении проблем с зависимостями)*
> * **Установите ffmpeg \
(для Linux: `sudo apt install ffmpeg` \
Для Windows: [*(Инструкция)*](https://phoenixnap.com/kb/ffmpeg-windows))**
> * **Установите и запустите postgresql** [_**(Инструкция)**_](https://www.postgresql.org/download/)
> * Создайте новую БД (стандартное название - viktor_bot) [_**(Инструкция)**_](https://postgrespro.ru/docs/postgresql/9.5/manage-ag-createdb)
> * Переименуйте файл `.env.example` в `.env` и **заполните его токенами и данными для подключения к БД** *(про токены смотрите ниже)*
> * Выставите **Privileged Gateway Intents** в [настройках бота](https://discord.com/developers/applications/)
> * **Скопируйте ссылку на бота** со скопами *bot* и *application.commands*. Также рекомендуется выдать ему права администратора
> * Запустите `main.py` в корневой папке


>**Решение проблем с зависимостью**
>* Закомментируйте строчку с `vkwave` в `requirements.txt`
>* Установите все остальные пакеты (`pip install -r requirements.txt`)
>* Установите `vkwave` (`pip install vkwave`)
>* Установите `typing_extensions==4.5.0` (`pip install --upgrade typing_extensions==4.5.0`)

> **Необходимые токены**
> 1. **DC_TOKEN** Токен Discord Бота получается в [настройках бота](https://discord.com/developers/applications/)
> 2. **VK_TOKEN** VK токен - можно получить [тут](https://vkhost.github.io/) (в данный момент нормально работает токен от Маруси)
> 3. **GENIUS_TOKEN** Токен Genius Lyrics - получать [тут](https://genius.com/api-clients) *(CLIENT ACCESS TOKEN)*